"""
Sistema de autenticação e identificação de operadores
"""
import streamlit as st

def check_login():
    """Verifica se o usuário está logado, se não, exibe formulário de login"""
    
    # Inicializar session_state se necessário
    if 'operador_logado' not in st.session_state:
        st.session_state.operador_logado = None
    
    # Se não está logado, mostrar formulário
    if st.session_state.operador_logado is None:
        show_login_form()
        return False
    
    return True

def show_login_form():
    """Exibe formulário de login/identificação do operador"""
    
    st.warning("🔐 Por favor, identifique-se para continuar")
    
    with st.form("login_form"):
        st.markdown("### 👤 Identificação do Operador")
        
        nome_operador = st.text_input(
            "Nome do Operador:",
            placeholder="Digite seu nome completo",
            help="Este nome será registrado em todas as catalogações que você fizer"
        )
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            botao_entrar = st.form_submit_button("🔓 Entrar", type="primary", use_container_width=True)
        
        if botao_entrar:
            if nome_operador.strip():
                st.session_state.operador_logado = nome_operador.strip()
                st.success(f"✅ Bem-vindo(a), {nome_operador}!")
                st.rerun()
            else:
                st.error("❌ Por favor, digite seu nome para continuar.")

def get_operador_nome():
    """Retorna o nome do operador logado"""
    return st.session_state.get('operador_logado', 'Não identificado')

def logout():
    """Faz logout do operador atual"""
    if 'operador_logado' in st.session_state:
        del st.session_state.operador_logado
    st.rerun()

def show_user_info():
    """Exibe informações do usuário logado na sidebar"""
    if st.session_state.get('operador_logado'):
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Operador")
            st.info(f"**{st.session_state.operador_logado}**")
            
            if st.button("🚪 Sair", use_container_width=True):
                logout()

