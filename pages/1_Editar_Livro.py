import streamlit as st
from supabase import create_client, Client
import pandas as pd
import sys
import os
import time

# Adicionar o diretório pai ao path para importar utils_auth
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_auth import check_login, get_operador_nome, show_user_info

# Configuração da página
st.set_page_config(
    page_title="Editar Livro",
    page_icon="✍️",
    layout="wide"
)

# Verificar login
if not check_login():
    st.stop()

# Mostrar info do usuário
show_user_info()

# Inicializar cliente Supabase
@st.cache_resource
def init_supabase():
    """Inicializa conexão com Supabase usando secrets do Streamlit"""
    try:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro ao conectar com o Supabase. Verifique os segredos do Streamlit.")
        st.code(e)
        st.stop()

supabase = init_supabase()

# Funções auxiliares
def buscar_livros(termo_busca, tipo_busca="titulo", filtrar_por_operador=True):
    """Busca livros por título ou código de barras com JOIN na tabela genero"""
    try:
        # Iniciar query
        query = supabase.table('livro').select("""
            id,
            codigo_barras,
            titulo,
            autor,
            editora,
            created_at,
            operador_nome,
            genero:genero-id(id, nome)
        """)
        
        # Aplicar filtro de busca
        if tipo_busca == "titulo":
            query = query.ilike('titulo', f'%{termo_busca}%')
        else:
            query = query.eq('codigo_barras', termo_busca)
        
        # Filtrar por operador se solicitado
        if filtrar_por_operador:
            operador_atual = get_operador_nome()
            query = query.eq('operador_nome', operador_atual)
        
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao buscar livros: {e}")
        return []

def buscar_todos_generos():
    """Busca todos os gêneros disponíveis"""
    try:
        response = supabase.table('genero').select('id, nome').order('nome').execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao buscar gêneros: {e}")
        return []

def atualizar_livro(livro_id, dados_atualizados):
    """Atualiza um livro no banco de dados"""
    try:
        response = supabase.table('livro').update(dados_atualizados).eq('id', livro_id).execute()
        return response.data is not None
    except Exception as e:
        st.error(f"Erro ao atualizar livro: {e}")
        return False

def excluir_livro(livro_id):
    """Exclui um livro do banco de dados"""
    try:
        response = supabase.table('livro').delete().eq('id', livro_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir livro: {e}")
        return False

# Função para carregar todos os livros do operador
@st.cache_data(ttl=60)
def carregar_livros_operador(operador_nome):
    """Carrega todos os livros de um operador específico"""
    try:
        response = supabase.table('livro').select("""
            id,
            codigo_barras,
            titulo,
            autor,
            editora,
            created_at,
            operador_nome,
            genero:genero-id(id, nome)
        """).eq('operador_nome', operador_nome).order('created_at', desc=True).execute()
        
        if response.data:
            # Processar dados para formato de tabela
            processed_data = []
            for row in response.data:
                processed_row = {
                    'id': row['id'],
                    'Código de Barras': row.get('codigo_barras', ''),
                    'Título': row.get('titulo', ''),
                    'Autor': row.get('autor', ''),
                    'Editora': row.get('editora', ''),
                    'Gênero': row.get('genero', {}).get('nome', '') if row.get('genero') else '',
                    'genero_id': row.get('genero', {}).get('id') if row.get('genero') else None,
                    'Catalogado em': row.get('created_at', '')
                }
                processed_data.append(processed_row)
            
            return pd.DataFrame(processed_data)
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar livros: {e}")
        return pd.DataFrame()

# Interface principal
st.title("✍️ Editar Livros")
st.markdown("---")

# Informação do operador atual
operador_atual = get_operador_nome()
st.info(f"👤 **Operador:** {operador_atual} | Editando seus livros catalogados")

# Carregar livros automaticamente
df_livros = carregar_livros_operador(operador_atual)

if df_livros.empty:
    st.warning("📚 Você ainda não catalogou nenhum livro.")
    st.info("💡 **Dica:** Vá para a página principal para começar a catalogar!")
else:
    # Estatísticas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Total de Livros", len(df_livros))
    with col2:
        st.metric("✍️ Autores Únicos", df_livros['Autor'].nunique())
    with col3:
        st.metric("📖 Gêneros Únicos", df_livros['Gênero'].nunique())
    
    st.markdown("---")
    
    # Opção de busca (secundária, em expander)
    with st.expander("🔍 Buscar Livro Específico (Opcional)", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            termo_busca = st.text_input(
                "Digite o título ou código de barras:",
                placeholder="Ex: Harry Potter ou 9788532530802",
                key="termo_busca"
            )
        
        with col2:
            tipo_busca = st.selectbox(
                "Buscar por:",
                ["titulo", "codigo_barras"],
                format_func=lambda x: "Título" if x == "titulo" else "Código"
            )
        
        if st.button("🔍 Buscar", type="primary"):
            if termo_busca:
                if tipo_busca == "titulo":
                    df_filtrado = df_livros[df_livros['Título'].str.contains(termo_busca, case=False, na=False)]
                else:
                    df_filtrado = df_livros[df_livros['Código de Barras'].str.contains(termo_busca, case=False, na=False)]
                
                if not df_filtrado.empty:
                    st.session_state.df_filtrado = df_filtrado
                    st.success(f"✅ {len(df_filtrado)} livro(s) encontrado(s)")
                    st.rerun()
                else:
                    st.warning(f"❌ Nenhum livro encontrado para '{termo_busca}'")
        
        if st.button("🔄 Limpar Busca"):
            if 'df_filtrado' in st.session_state:
                del st.session_state.df_filtrado
            st.rerun()
    
    st.markdown("---")
    
    # Usar df filtrado se existir, senão usar todos
    df_exibir = st.session_state.get('df_filtrado', df_livros)
    
    # Título da tabela
    if 'df_filtrado' in st.session_state:
        st.subheader(f"📝 Editando {len(df_exibir)} livro(s) (busca ativa)")
    else:
        st.subheader(f"📝 Seus Livros ({len(df_exibir)} total)")
    
    st.markdown("**✏️ Clique em uma célula para editar | 💾 Clique em 'Salvar Alterações' após editar**")
    
    # Preparar DataFrame para edição
    df_editavel = df_exibir.copy()
    
    # Colunas para exibir (sem id e genero_id)
    colunas_exibir = ['Código de Barras', 'Título', 'Autor', 'Editora', 'Gênero']
    
    # Configuração de colunas para o data_editor
    column_config = {
        'Código de Barras': st.column_config.TextColumn(
            'ISBN/Código',
            help="Código de barras do livro",
            max_chars=50,
            width="medium"
        ),
        'Título': st.column_config.TextColumn(
            'Título',
            help="Título do livro",
            max_chars=200,
            width="large"
        ),
        'Autor': st.column_config.TextColumn(
            'Autor',
            help="Nome do autor",
            max_chars=100,
            width="medium"
        ),
        'Editora': st.column_config.TextColumn(
            'Editora',
            help="Nome da editora",
            max_chars=100,
            width="medium"
        ),
        'Gênero': st.column_config.SelectboxColumn(
            'Gênero',
            help="Gênero literário",
            options=[g['nome'] for g in buscar_todos_generos()],
            width="medium"
        )
    }
    
    # Tabela editável
    df_edited = st.data_editor(
        df_editavel[colunas_exibir],
        column_config=column_config,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        key="editor_livros"
    )
    
    # Detectar mudanças e salvar
    if not df_edited.equals(df_editavel[colunas_exibir]):
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                sucesso = 0
                erros = 0
                
                # Comparar linha por linha
                for idx in df_edited.index:
                    if not df_edited.loc[idx].equals(df_editavel.loc[idx, colunas_exibir]):
                        # Linha foi editada
                        livro_id = df_editavel.loc[idx, 'id']
                        
                        # Buscar ID do gênero pelo nome
                        genero_nome = df_edited.loc[idx, 'Gênero']
                        todos_generos = buscar_todos_generos()
                        genero_id = next((g['id'] for g in todos_generos if g['nome'] == genero_nome), None)
                        
                        if genero_id:
                            # Preparar dados atualizados
                            dados_atualizados = {
                                'codigo_barras': df_edited.loc[idx, 'Código de Barras'],
                                'titulo': df_edited.loc[idx, 'Título'],
                                'autor': df_edited.loc[idx, 'Autor'],
                                'editora': df_edited.loc[idx, 'Editora'],
                                'genero-id': genero_id
                            }
                            
                            # Atualizar no banco
                            if atualizar_livro(livro_id, dados_atualizados):
                                sucesso += 1
                            else:
                                erros += 1
                        else:
                            erros += 1
                
                # Mensagem de resultado
                if sucesso > 0:
                    st.success(f"✅ {sucesso} livro(s) atualizado(s) com sucesso!")
                    st.balloons()
                    carregar_livros_operador.clear()
                    time.sleep(1)
                    st.rerun()
                
                if erros > 0:
                    st.error(f"❌ {erros} erro(s) ao atualizar")
        
        with col2:
            st.info("ℹ️ Você tem alterações não salvas. Clique em 'Salvar Alterações' para confirmar.")
    
    # Opção de exclusão
    st.markdown("---")
    with st.expander("🗑️ Excluir Livros", expanded=False):
        st.warning("⚠️ **ATENÇÃO:** A exclusão é permanente e não pode ser desfeita!")
        
        # Selecionar livros para excluir
        titulos_para_excluir = st.multiselect(
            "Selecione os livros que deseja excluir:",
            options=df_exibir['Título'].tolist(),
            help="Você pode selecionar múltiplos livros"
        )
        
        if titulos_para_excluir:
            st.warning(f"📚 **{len(titulos_para_excluir)} livro(s) selecionado(s) para exclusão:**")
            for titulo in titulos_para_excluir:
                st.write(f"- {titulo}")
            
            confirma_exclusao = st.checkbox(
                "✅ Sim, tenho certeza que quero excluir estes livros permanentemente",
                key="confirma_exclusao_multipla"
            )
            
            if confirma_exclusao:
                if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="primary"):
                    sucesso = 0
                    erros = 0
                    
                    for titulo in titulos_para_excluir:
                        livro_id = df_exibir[df_exibir['Título'] == titulo]['id'].iloc[0]
                        if excluir_livro(livro_id):
                            sucesso += 1
                        else:
                            erros += 1
                    
                    if sucesso > 0:
                        st.success(f"✅ {sucesso} livro(s) excluído(s) com sucesso!")
                        carregar_livros_operador.clear()
                        time.sleep(1)
                        st.rerun()
                    
                    if erros > 0:
                        st.error(f"❌ {erros} erro(s) ao excluir")

# Instruções
st.markdown("---")
with st.expander("ℹ️ Como usar esta página", expanded=False):
    st.markdown("""
    **📝 Edição Rápida em Tabela:**
    
    1. 📊 **Visualização:** Todos os seus livros aparecem automaticamente em uma tabela
    2. ✏️ **Editar:** Clique em qualquer célula para editar diretamente
    3. 🔄 **Gênero:** Use o dropdown na coluna "Gênero" para selecionar
    4. 💾 **Salvar:** Clique em "Salvar Alterações" para confirmar as edições
    
    **🔍 Busca Opcional:**
    - Expanda a seção "Buscar Livro Específico" se quiser filtrar
    - Digite título ou código de barras
    - A tabela mostrará apenas os resultados filtrados
    
    **🗑️ Excluir Livros:**
    - Expanda a seção "Excluir Livros"
    - Selecione um ou mais livros na lista
    - Confirme a exclusão (ação permanente!)
    
    **⚠️ Importante:**
    - ✅ Você vê **apenas os livros catalogados por você**
    - ✅ Edite **múltiplos livros** de uma vez
    - ✅ As alterações são salvas **apenas** após clicar em "Salvar Alterações"
    - ❌ Exclusões são **permanentes** e não podem ser desfeitas
    
    **💡 Dicas:**
    - Ordene a tabela clicando nos cabeçalhos das colunas
    - Edite várias células antes de salvar
    - Use Ctrl+F para buscar na tabela
    """)

