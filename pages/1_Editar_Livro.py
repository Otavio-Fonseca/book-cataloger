import streamlit as st
from supabase import create_client, Client
import pandas as pd
import sys
import os

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

# Interface principal
st.title("✍️ Editar ou Excluir Livro")
st.markdown("---")

# Seção de busca
st.header("🔍 Buscar Livro")

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    termo_busca = st.text_input(
        "Digite o título ou código de barras do livro:",
        placeholder="Ex: Harry Potter ou 9788532530802",
        key="termo_busca"
    )

with col2:
    tipo_busca = st.selectbox(
        "Buscar por:",
        ["titulo", "codigo_barras"],
        format_func=lambda x: "Título" if x == "titulo" else "Código de Barras"
    )

with col3:
    filtrar_operador = st.checkbox(
        "Apenas meus livros",
        value=True,
        help="Marque para ver apenas os livros catalogados por você"
    )

if st.button("🔍 Buscar", type="primary"):
    if termo_busca:
        st.session_state.resultados_busca = buscar_livros(termo_busca, tipo_busca, filtrar_operador)
        st.session_state.termo_buscado = termo_busca
        st.session_state.filtrou_operador = filtrar_operador
    else:
        st.warning("Por favor, digite um termo de busca.")

# Exibir resultados da busca
if 'resultados_busca' in st.session_state and st.session_state.resultados_busca:
    st.markdown("---")
    st.subheader(f"📚 Resultados da Busca: '{st.session_state.termo_buscado}'")
    
    # Mostrar informação sobre o filtro
    if st.session_state.get('filtrou_operador', False):
        st.info(f"**{len(st.session_state.resultados_busca)}** livro(s) encontrado(s) **catalogados por você** ({get_operador_nome()})")
    else:
        st.info(f"**{len(st.session_state.resultados_busca)}** livro(s) encontrado(s) (todos os operadores)")
    
    for idx, livro in enumerate(st.session_state.resultados_busca):
        genero_nome = livro.get('genero', {}).get('nome', 'N/A') if livro.get('genero') else 'N/A'
        
        with st.expander(f"📖 {livro['titulo']} - {livro['autor']}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Código de Barras:** {livro.get('codigo_barras', 'N/A')}")
                st.write(f"**Autor:** {livro.get('autor', 'N/A')}")
                st.write(f"**Editora:** {livro.get('editora', 'N/A')}")
                st.write(f"**Gênero:** {genero_nome}")
                st.write(f"**Operador:** {livro.get('operador_nome', 'N/A')}")
                st.write(f"**Catalogado em:** {livro.get('created_at', 'N/A')}")
            
            with col2:
                if st.button("✏️ Carregar para Edição", key=f"edit_{livro['id']}_{idx}"):
                    st.session_state.livro_selecionado = livro
                    st.rerun()

elif 'resultados_busca' in st.session_state and not st.session_state.resultados_busca:
    st.warning(f"Nenhum livro encontrado para '{st.session_state.termo_buscado}'")

# Formulário de edição
if 'livro_selecionado' in st.session_state:
    st.markdown("---")
    st.header("📝 Editar Dados do Livro")
    
    livro = st.session_state.livro_selecionado
    genero_atual = livro.get('genero', {})
    genero_id_atual = genero_atual.get('id') if genero_atual else None
    genero_nome_atual = genero_atual.get('nome', 'N/A') if genero_atual else 'N/A'
    
    st.info(f"📚 Editando: **{livro['titulo']}** (ID: {livro['id']})")
    
    with st.form("form_edicao"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📚 Informações Básicas")
            novo_codigo_barras = st.text_input(
                "Código de Barras:",
                value=livro.get('codigo_barras', ''),
                help="ISBN ou código de barras do livro"
            )
            novo_titulo = st.text_input(
                "Título:",
                value=livro.get('titulo', ''),
                help="Título completo do livro"
            )
            novo_autor = st.text_input(
                "Autor:",
                value=livro.get('autor', ''),
                help="Nome do(s) autor(es)"
            )
        
        with col2:
            st.markdown("#### 🏢 Detalhes Adicionais")
            nova_editora = st.text_input(
                "Editora:",
                value=livro.get('editora', ''),
                help="Nome da editora"
            )
            
            # Buscar todos os gêneros para o selectbox
            todos_generos = buscar_todos_generos()
            generos_opcoes = {g['id']: g['nome'] for g in todos_generos}
            
            # Encontrar o índice do gênero atual
            genero_index = 0
            if genero_id_atual and genero_id_atual in generos_opcoes:
                genero_index = list(generos_opcoes.keys()).index(genero_id_atual)
            
            novo_genero_id = st.selectbox(
                "Gênero:",
                options=list(generos_opcoes.keys()),
                format_func=lambda x: generos_opcoes[x],
                index=genero_index,
                help="Selecione o gênero do livro"
            )
            
            novo_operador = st.text_input(
                "Operador:",
                value=livro.get('operador_nome', ''),
                help="Nome do operador que catalogou"
            )
        
        st.markdown("---")
        
        # Botões de ação
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            botao_salvar = st.form_submit_button("💾 Salvar Alterações", type="primary")
        
        with col2:
            botao_excluir = st.form_submit_button("🗑️ Excluir Livro", type="secondary")
        
        with col3:
            botao_cancelar = st.form_submit_button("❌ Cancelar")
        
        # Processamento do formulário
        if botao_salvar:
            # Validação
            if not novo_titulo.strip() or not novo_autor.strip() or not nova_editora.strip():
                st.error("❌ Título, Autor e Editora são campos obrigatórios!")
            else:
                # Preparar dados para atualização
                dados_atualizados = {
                    'codigo_barras': novo_codigo_barras.strip(),
                    'titulo': novo_titulo.strip(),
                    'autor': novo_autor.strip(),
                    'editora': nova_editora.strip(),
                    'genero-id': novo_genero_id,
                    'operador_nome': novo_operador.strip() if novo_operador else None
                }
                
                # Atualizar no banco
                if atualizar_livro(livro['id'], dados_atualizados):
                    st.success(f"✅ Livro '{novo_titulo}' atualizado com sucesso!")
                    st.balloons()
                    
                    # Limpar sessão
                    if 'livro_selecionado' in st.session_state:
                        del st.session_state.livro_selecionado
                    if 'resultados_busca' in st.session_state:
                        del st.session_state.resultados_busca
                    
                    st.rerun()
        
        elif botao_excluir:
            # Área de confirmação de exclusão
            st.markdown("---")
            st.warning("⚠️ **ATENÇÃO: Esta ação não pode ser desfeita!**")
            
            confirmacao = st.checkbox(
                "✅ Sim, tenho certeza que quero excluir este livro permanentemente.",
                key="confirma_exclusao"
            )
            
            if confirmacao:
                if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="primary"):
                    if excluir_livro(livro['id']):
                        st.success(f"✅ Livro '{livro['titulo']}' excluído com sucesso!")
                        
                        # Limpar sessão
                        if 'livro_selecionado' in st.session_state:
                            del st.session_state.livro_selecionado
                        if 'resultados_busca' in st.session_state:
                            del st.session_state.resultados_busca
                        
                        st.rerun()
        
        elif botao_cancelar:
            # Limpar sessão
            if 'livro_selecionado' in st.session_state:
                del st.session_state.livro_selecionado
            st.rerun()

# Instruções
with st.expander("ℹ️ Como usar esta página", expanded=False):
    st.markdown("""
    **Passos para editar um livro:**
    
    1. 🔍 Use o campo de busca para encontrar o livro (por título ou código de barras)
    2. 📖 Clique em um dos resultados para ver os detalhes
    3. ✏️ Clique em "Carregar para Edição" no livro desejado
    4. 📝 Edite os campos necessários no formulário
    5. 💾 Clique em "Salvar Alterações" para confirmar
    
    **Para excluir um livro:**
    
    1. Siga os passos 1-3 acima
    2. 🗑️ Clique em "Excluir Livro"
    3. ✅ Marque a caixa de confirmação
    4. 🗑️ Clique em "CONFIRMAR EXCLUSÃO"
    
    ⚠️ **Importante:** A exclusão é permanente e não pode ser desfeita!
    """)

