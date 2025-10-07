import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="Gerenciar Gêneros",
    page_icon="📚",
    layout="wide"
)

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
@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_generos():
    """Carrega todos os gêneros do banco de dados"""
    try:
        response = supabase.table('genero').select('*').order('nome').execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=['id', 'nome', 'created_at'])
    except Exception as e:
        st.error(f"Erro ao carregar gêneros: {e}")
        return pd.DataFrame(columns=['id', 'nome', 'created_at'])

def adicionar_genero(nome_genero):
    """Adiciona um novo gênero ao banco de dados"""
    try:
        # Verificar se já existe
        response_check = supabase.table('genero').select('id').eq('nome', nome_genero).execute()
        if response_check.data:
            st.warning(f"⚠️ O gênero '{nome_genero}' já existe!")
            return False
        
        # Inserir novo gênero
        response = supabase.table('genero').insert({'nome': nome_genero}).execute()
        if response.data:
            carregar_generos.clear()  # Limpar cache
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar gênero: {e}")
        return False

def atualizar_genero(genero_id, novo_nome):
    """Atualiza o nome de um gênero"""
    try:
        response = supabase.table('genero').update({'nome': novo_nome}).eq('id', genero_id).execute()
        if response.data:
            carregar_generos.clear()  # Limpar cache
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar gênero: {e}")
        return False

def excluir_genero(genero_id):
    """Exclui um gênero do banco de dados"""
    try:
        # Verificar se há livros usando este gênero
        response_check = supabase.table('livro').select('id', count='exact').eq('genero-id', genero_id).execute()
        
        if response_check.count and response_check.count > 0:
            st.error(f"❌ Não é possível excluir este gênero pois existem {response_check.count} livro(s) usando-o!")
            st.info("💡 **Dica:** Primeiro, altere o gênero dos livros que o utilizam, depois tente excluir novamente.")
            return False
        
        # Se não há livros, pode excluir
        response = supabase.table('genero').delete().eq('id', genero_id).execute()
        carregar_generos.clear()  # Limpar cache
        return True
    except Exception as e:
        st.error(f"Erro ao excluir gênero: {e}")
        return False

def contar_livros_por_genero(genero_id):
    """Conta quantos livros usam um gênero específico"""
    try:
        response = supabase.table('livro').select('id', count='exact').eq('genero-id', genero_id).execute()
        return response.count if response.count else 0
    except Exception as e:
        return 0

# Interface principal
st.title("📚 Gerenciar Gêneros Literários")
st.markdown("---")

# Seção: Adicionar novo gênero
st.header("➕ Adicionar Novo Gênero")

with st.form("form_adicionar_genero", clear_on_submit=True):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        novo_genero = st.text_input(
            "Nome do Novo Gênero:",
            placeholder="Ex: Romance, Ficção Científica, História...",
            help="Digite o nome do gênero literário que deseja adicionar"
        )
    
    with col2:
        st.write("")  # Espaçamento
        st.write("")  # Espaçamento
        botao_adicionar = st.form_submit_button("➕ Adicionar Gênero", type="primary")
    
    if botao_adicionar:
        if novo_genero.strip():
            if adicionar_genero(novo_genero.strip()):
                st.success(f"✅ Gênero '{novo_genero}' adicionado com sucesso!")
                st.balloons()
                st.rerun()
        else:
            st.warning("⚠️ Por favor, digite o nome do gênero.")

st.markdown("---")

# Seção: Listar e gerenciar gêneros existentes
st.header("📋 Gêneros Cadastrados")

df_generos = carregar_generos()

if not df_generos.empty:
    # Estatísticas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Gêneros", len(df_generos))
    with col2:
        st.metric("Último Adicionado", df_generos.iloc[-1]['nome'] if len(df_generos) > 0 else "N/A")
    
    st.markdown("---")
    
    # Tabela interativa com opções de edição e exclusão
    st.subheader("🔧 Gerenciar Gêneros")
    
    # Adicionar contagem de livros para cada gênero
    if 'contagens_livros' not in st.session_state:
        st.session_state.contagens_livros = {}
    
    # Exibir cada gênero com opções
    for idx, row in df_generos.iterrows():
        genero_id = row['id']
        genero_nome = row['nome']
        
        # Contar livros (com cache na sessão)
        if genero_id not in st.session_state.contagens_livros:
            st.session_state.contagens_livros[genero_id] = contar_livros_por_genero(genero_id)
        
        qtd_livros = st.session_state.contagens_livros[genero_id]
        
        with st.expander(f"📖 {genero_nome} ({qtd_livros} livro{'s' if qtd_livros != 1 else ''})", expanded=False):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Formulário inline para edição
                with st.form(f"form_edit_{genero_id}"):
                    novo_nome = st.text_input(
                        "Novo nome:",
                        value=genero_nome,
                        key=f"input_{genero_id}",
                        help="Edite o nome do gênero"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.form_submit_button("💾 Salvar", type="primary"):
                            if novo_nome.strip() and novo_nome.strip() != genero_nome:
                                if atualizar_genero(genero_id, novo_nome.strip()):
                                    st.success(f"✅ Gênero atualizado para '{novo_nome}'!")
                                    st.rerun()
                            elif novo_nome.strip() == genero_nome:
                                st.info("ℹ️ Nenhuma alteração detectada.")
                            else:
                                st.warning("⚠️ Digite um nome válido.")
            
            with col2:
                st.write("")
                st.write("")
                if st.button("🗑️ Excluir", key=f"del_{genero_id}", type="secondary"):
                    st.session_state.genero_para_excluir = genero_id
                    st.session_state.genero_nome_excluir = genero_nome
            
            with col3:
                st.write("")
                st.write("")
                st.caption(f"ID: {genero_id}")
    
    # Confirmação de exclusão (fora do expander)
    if 'genero_para_excluir' in st.session_state:
        st.markdown("---")
        st.warning(f"⚠️ **Confirmar exclusão do gênero:** '{st.session_state.genero_nome_excluir}'?")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ SIM, Excluir", type="primary"):
                if excluir_genero(st.session_state.genero_para_excluir):
                    st.success(f"✅ Gênero '{st.session_state.genero_nome_excluir}' excluído com sucesso!")
                    del st.session_state.genero_para_excluir
                    del st.session_state.genero_nome_excluir
                    if 'contagens_livros' in st.session_state:
                        del st.session_state.contagens_livros
                    st.rerun()
        
        with col2:
            if st.button("❌ NÃO, Cancelar"):
                del st.session_state.genero_para_excluir
                del st.session_state.genero_nome_excluir
                st.rerun()
    
    st.markdown("---")
    
    # Visualização em tabela (modo leitura)
    st.subheader("📊 Visualização em Tabela")
    
    # Preparar dados para exibição
    df_exibicao = df_generos[['id', 'nome', 'created_at']].copy()
    df_exibicao.columns = ['ID', 'Nome do Gênero', 'Criado em']
    
    # Adicionar coluna de contagem de livros
    df_exibicao['Qtd. Livros'] = df_exibicao['ID'].apply(
        lambda x: st.session_state.contagens_livros.get(x, 0)
    )
    
    st.dataframe(
        df_exibicao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Nome do Gênero": st.column_config.TextColumn("Nome do Gênero", width="large"),
            "Criado em": st.column_config.DatetimeColumn("Criado em", format="DD/MM/YYYY HH:mm"),
            "Qtd. Livros": st.column_config.NumberColumn("Qtd. Livros", width="small")
        }
    )
    
    # Botão para exportar
    csv = df_exibicao.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar lista de gêneros (CSV)",
        data=csv,
        file_name="generos_literarios.csv",
        mime="text/csv",
    )

else:
    st.info("📚 Nenhum gênero cadastrado ainda. Adicione o primeiro gênero acima!")

# Instruções
with st.expander("ℹ️ Como usar esta página", expanded=False):
    st.markdown("""
    **Para adicionar um novo gênero:**
    
    1. ➕ Digite o nome do gênero no campo "Nome do Novo Gênero"
    2. 🔘 Clique em "Adicionar Gênero"
    3. ✅ O gênero será adicionado à lista
    
    **Para editar um gênero:**
    
    1. 📖 Clique no gênero desejado na lista para expandir
    2. ✏️ Altere o nome no campo de texto
    3. 💾 Clique em "Salvar" para confirmar a alteração
    
    **Para excluir um gênero:**
    
    1. 📖 Clique no gênero desejado na lista
    2. 🗑️ Clique em "Excluir"
    3. ✅ Confirme a exclusão
    
    ⚠️ **Importante:** 
    - Não é possível excluir gêneros que estão sendo usados por livros
    - Primeiro, altere o gênero dos livros, depois exclua o gênero desejado
    - A contagem de livros é atualizada automaticamente
    """)

# Botão de atualizar dados
if st.button("🔄 Atualizar Lista de Gêneros"):
    carregar_generos.clear()
    if 'contagens_livros' in st.session_state:
        del st.session_state.contagens_livros
    st.rerun()

