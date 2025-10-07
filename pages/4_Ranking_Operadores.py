import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Adicionar o diretório pai ao path para importar utils_auth
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils_auth import check_login, get_operador_nome, show_user_info

# Configuração da página
st.set_page_config(
    page_title="Ranking de Operadores",
    page_icon="🏆",
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

# Data de início da competição
DATA_INICIO_COMPETICAO = datetime(2025, 10, 7, 0, 0, 0)

# Funções auxiliares
@st.cache_data(ttl=60)  # Cache de 1 minuto (dados em tempo real)
def get_ranking_data():
    """Obtém dados de catalogação de todos os operadores desde a data de início"""
    try:
        # Buscar todos os livros desde a data de início
        data_inicio_iso = DATA_INICIO_COMPETICAO.isoformat()
        
        response = supabase.table('livro').select("""
            id,
            operador_nome,
            created_at
        """).gte('created_at', data_inicio_iso).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def get_badge(posicao):
    """Retorna emoji de medalha baseado na posição"""
    badges = {
        1: "🥇",
        2: "🥈", 
        3: "🥉"
    }
    return badges.get(posicao, "📊")

def get_achievement_badges(quantidade):
    """Retorna badges de conquistas baseado na quantidade"""
    achievements = []
    
    if quantidade >= 100:
        achievements.append("💯 Centenário")
    if quantidade >= 50:
        achievements.append("⭐ Estrela")
    if quantidade >= 25:
        achievements.append("🎯 Atirador")
    if quantidade >= 10:
        achievements.append("🌟 Iniciante")
    if quantidade >= 5:
        achievements.append("🔰 Novato")
    
    return achievements

def calculate_streak(df_operador):
    """Calcula sequência de dias consecutivos catalogando"""
    if df_operador.empty:
        return 0
    
    # Extrair apenas as datas (sem hora)
    df_operador = df_operador.copy()
    df_operador['data'] = df_operador['created_at'].dt.date
    
    # Datas únicas ordenadas
    datas_unicas = sorted(df_operador['data'].unique(), reverse=True)
    
    if not datas_unicas:
        return 0
    
    # Verificar se catalogou hoje
    hoje = datetime.now().date()
    if datas_unicas[0] != hoje and datas_unicas[0] != (hoje - timedelta(days=1)):
        return 0
    
    # Contar dias consecutivos
    streak = 1
    for i in range(len(datas_unicas) - 1):
        diff = (datas_unicas[i] - datas_unicas[i + 1]).days
        if diff == 1:
            streak += 1
        else:
            break
    
    return streak

# Interface principal
st.title("🏆 Ranking de Operadores - Competição de Catalogação")
st.markdown("---")

# Banner da competição
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            color: white;
            margin-bottom: 20px;">
    <h2>🎯 COMPETIÇÃO DE CATALOGAÇÃO 2025</h2>
    <p style="font-size: 18px; margin: 10px 0;">
        Desde 07 de Outubro de 2025 | Ranking atualizado em tempo real
    </p>
    <p style="font-size: 16px; margin: 0;">
        🏆 Catalogar mais livros = Subir no ranking = Reconhecimento! 🏆
    </p>
</div>
""", unsafe_allow_html=True)

# Carregar dados
df_total = get_ranking_data()

if df_total.empty:
    st.info("📚 Nenhum livro catalogado desde o início da competição.")
    st.markdown("**Data de início:** 07/10/2025")
    st.markdown("**Seja o primeiro a catalogar e liderar o ranking!** 🚀")
else:
    # Calcular estatísticas por operador
    ranking = df_total.groupby('operador_nome').size().reset_index(name='quantidade')
    ranking = ranking.sort_values('quantidade', ascending=False).reset_index(drop=True)
    ranking['posicao'] = ranking.index + 1
    ranking['badge'] = ranking['posicao'].apply(get_badge)
    
    # Estatísticas gerais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📚 Total Catalogado",
            f"{len(df_total):,}".replace(',', '.'),
            help="Total de livros catalogados na competição"
        )
    
    with col2:
        st.metric(
            "👥 Operadores Ativos",
            len(ranking),
            help="Número de operadores participando"
        )
    
    with col3:
        dias_competicao = (datetime.now() - DATA_INICIO_COMPETICAO).days + 1
        st.metric(
            "📅 Dias de Competição",
            dias_competicao,
            help="Dias desde o início"
        )
    
    with col4:
        media_dia = len(df_total) / dias_competicao if dias_competicao > 0 else 0
        st.metric(
            "📊 Média Diária",
            f"{media_dia:.1f}",
            help="Média de livros por dia"
        )
    
    st.markdown("---")
    
    # PÓDIO - TOP 3
    st.header("🏆 Pódio dos Campeões")
    
    if len(ranking) >= 1:
        # Preparar dados do pódio
        top3 = ranking.head(3)
        
        # Layout do pódio (2º, 1º, 3º)
        col1, col2, col3 = st.columns([1, 1.2, 1])
        
        # 2º Lugar
        if len(top3) >= 2:
            with col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #C0C0C0 0%, #E8E8E8 100%);
                            padding: 20px;
                            border-radius: 10px;
                            text-align: center;
                            margin-top: 40px;">
                    <div style="font-size: 50px;">🥈</div>
                    <div style="font-size: 24px; font-weight: bold; color: #333; margin: 10px 0;">
                        {top3.iloc[1]['operador_nome']}
                    </div>
                    <div style="font-size: 36px; color: #555; font-weight: bold;">
                        {top3.iloc[1]['quantidade']}
                    </div>
                    <div style="font-size: 14px; color: #666;">
                        livros catalogados
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # 1º Lugar (destaque maior)
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                        padding: 30px;
                        border-radius: 10px;
                        text-align: center;
                        box-shadow: 0 8px 16px rgba(255,215,0,0.3);">
                <div style="font-size: 70px;">🥇</div>
                <div style="font-size: 28px; font-weight: bold; color: #333; margin: 10px 0;">
                    {top3.iloc[0]['operador_nome']}
                </div>
                <div style="font-size: 48px; color: #555; font-weight: bold;">
                    {top3.iloc[0]['quantidade']}
                </div>
                <div style="font-size: 16px; color: #666;">
                    livros catalogados
                </div>
                <div style="font-size: 20px; margin-top: 10px;">
                    👑 LÍDER ATUAL 👑
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 3º Lugar
        if len(top3) >= 3:
            with col3:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #CD7F32 0%, #E8C39E 100%);
                            padding: 20px;
                            border-radius: 10px;
                            text-align: center;
                            margin-top: 40px;">
                    <div style="font-size: 50px;">🥉</div>
                    <div style="font-size: 24px; font-weight: bold; color: #333; margin: 10px 0;">
                        {top3.iloc[2]['operador_nome']}
                    </div>
                    <div style="font-size: 36px; color: #555; font-weight: bold;">
                        {top3.iloc[2]['quantidade']}
                    </div>
                    <div style="font-size: 14px; color: #666;">
                        livros catalogados
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # RANKING COMPLETO
    st.header("📊 Ranking Completo")
    
    # Adicionar conquistas ao ranking
    ranking['conquistas'] = ranking['quantidade'].apply(get_achievement_badges)
    
    # Tabela de ranking com cores
    for idx, row in ranking.iterrows():
        col1, col2, col3, col4 = st.columns([0.5, 2, 1, 2])
        
        # Cor de fundo baseada na posição
        if row['posicao'] == 1:
            bg_color = "#FFF9E6"  # Dourado claro
        elif row['posicao'] == 2:
            bg_color = "#F5F5F5"  # Prata claro
        elif row['posicao'] == 3:
            bg_color = "#FFF0E6"  # Bronze claro
        else:
            bg_color = "white"
        
        with st.container():
            st.markdown(f"""
            <div style="background-color: {bg_color}; 
                        padding: 15px; 
                        border-radius: 8px; 
                        margin: 5px 0;
                        border: 1px solid #ddd;">
            """, unsafe_allow_html=True)
            
            with col1:
                st.markdown(f"### {row['badge']}")
                st.caption(f"#{row['posicao']}")
            
            with col2:
                st.markdown(f"### {row['operador_nome']}")
                if row['conquistas']:
                    st.caption(' '.join(row['conquistas']))
            
            with col3:
                st.metric("Livros", row['quantidade'])
            
            with col4:
                # Calcular progresso até próxima conquista
                prox_meta = None
                if row['quantidade'] < 5:
                    prox_meta = 5
                elif row['quantidade'] < 10:
                    prox_meta = 10
                elif row['quantidade'] < 25:
                    prox_meta = 25
                elif row['quantidade'] < 50:
                    prox_meta = 50
                elif row['quantidade'] < 100:
                    prox_meta = 100
                
                if prox_meta:
                    progresso = (row['quantidade'] / prox_meta) * 100
                    st.progress(progresso / 100)
                    st.caption(f"Faltam {prox_meta - row['quantidade']} para próxima conquista")
                else:
                    st.success("✅ Todas conquistas desbloqueadas!")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # GRÁFICO DE BARRAS - Comparação Visual
    st.header("📊 Comparação Visual")
    
    # Gráfico de barras horizontal
    fig_ranking = go.Figure()
    
    # Definir cores baseadas na posição
    cores = []
    for pos in ranking['posicao']:
        if pos == 1:
            cores.append('#FFD700')  # Ouro
        elif pos == 2:
            cores.append('#C0C0C0')  # Prata
        elif pos == 3:
            cores.append('#CD7F32')  # Bronze
        else:
            cores.append('#87CEEB')  # Azul claro
    
    fig_ranking.add_trace(go.Bar(
        y=ranking['operador_nome'],
        x=ranking['quantidade'],
        orientation='h',
        marker=dict(
            color=cores,
            line=dict(color='rgba(0,0,0,0.3)', width=2)
        ),
        text=ranking['quantidade'],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Livros: %{x}<br><extra></extra>'
    ))
    
    fig_ranking.update_layout(
        title=dict(
            text="🏆 Ranking de Catalogação",
            font=dict(size=24)
        ),
        xaxis_title="Quantidade de Livros Catalogados",
        yaxis_title="",
        height=max(400, len(ranking) * 60),
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig_ranking, use_container_width=True)
    
    st.markdown("---")
    
    # EVOLUÇÃO DIÁRIA
    st.header("📈 Evolução da Competição")
    
    # Agrupar por operador e data
    df_daily = df_total.copy()
    df_daily['data'] = df_daily['created_at'].dt.date
    
    # Pivot para ter cada operador como série
    daily_counts = df_daily.groupby(['data', 'operador_nome']).size().reset_index(name='quantidade')
    
    # Gráfico de linhas
    fig_evolucao = px.line(
        daily_counts,
        x='data',
        y='quantidade',
        color='operador_nome',
        title='Catalogação Diária por Operador',
        labels={'data': 'Data', 'quantidade': 'Livros por Dia', 'operador_nome': 'Operador'},
        markers=True
    )
    
    fig_evolucao.update_layout(
        height=400,
        hovermode='x unified',
        legend=dict(
            title="Operadores",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    st.plotly_chart(fig_evolucao, use_container_width=True)
    
    st.markdown("---")
    
    # PROGRESSO ACUMULADO
    st.header("📊 Progresso Acumulado")
    
    # Calcular acumulado por operador
    daily_counts_sorted = daily_counts.sort_values(['operador_nome', 'data'])
    daily_counts_sorted['acumulado'] = daily_counts_sorted.groupby('operador_nome')['quantidade'].cumsum()
    
    fig_acumulado = px.line(
        daily_counts_sorted,
        x='data',
        y='acumulado',
        color='operador_nome',
        title='Total Acumulado por Operador',
        labels={'data': 'Data', 'acumulado': 'Total Acumulado', 'operador_nome': 'Operador'},
        markers=True
    )
    
    fig_acumulado.update_layout(
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_acumulado, use_container_width=True)
    
    st.markdown("---")
    
    # SUA POSIÇÃO (destaque para o operador logado)
    st.header("🎯 Sua Performance")
    
    operador_atual = get_operador_nome()
    
    # Verificar se o operador atual está no ranking
    meu_ranking = ranking[ranking['operador_nome'] == operador_atual]
    
    if not meu_ranking.empty:
        minha_pos = meu_ranking.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🏅 Sua Posição",
                f"#{minha_pos['posicao']}",
                help="Sua posição no ranking geral"
            )
        
        with col2:
            st.metric(
                "📚 Seus Livros",
                minha_pos['quantidade'],
                help="Total de livros que você catalogou"
            )
        
        with col3:
            # Diferença para o líder
            if minha_pos['posicao'] > 1:
                lider = ranking.iloc[0]
                diff = lider['quantidade'] - minha_pos['quantidade']
                st.metric(
                    "🎯 Distância do Líder",
                    f"{diff} livros",
                    help=f"Faltam {diff} livros para alcançar {lider['operador_nome']}"
                )
            else:
                st.metric(
                    "👑 Status",
                    "LÍDER!",
                    help="Você está em primeiro lugar!"
                )
        
        with col4:
            # Calcular streak
            df_operador = df_total[df_total['operador_nome'] == operador_atual]
            streak = calculate_streak(df_operador)
            
            if streak > 0:
                st.metric(
                    "🔥 Sequência",
                    f"{streak} dias",
                    help="Dias consecutivos catalogando"
                )
            else:
                st.metric(
                    "🔥 Sequência",
                    "0 dias",
                    help="Catalogue hoje para iniciar uma sequência!"
                )
        
        # Conquistas do operador
        if minha_pos['conquistas']:
            st.markdown("### 🏅 Suas Conquistas")
            conquistas_html = ' '.join([f'<span style="background: #4CAF50; color: white; padding: 8px 15px; border-radius: 20px; margin: 5px; display: inline-block;">{badge}</span>' for badge in minha_pos['conquistas']])
            st.markdown(conquistas_html, unsafe_allow_html=True)
        
        # Próxima meta
        st.markdown("### 🎯 Próxima Meta")
        prox_meta = None
        if minha_pos['quantidade'] < 5:
            prox_meta = (5, "🔰 Novato")
        elif minha_pos['quantidade'] < 10:
            prox_meta = (10, "🌟 Iniciante")
        elif minha_pos['quantidade'] < 25:
            prox_meta = (25, "🎯 Atirador")
        elif minha_pos['quantidade'] < 50:
            prox_meta = (50, "⭐ Estrela")
        elif minha_pos['quantidade'] < 100:
            prox_meta = (100, "💯 Centenário")
        
        if prox_meta:
            faltam = prox_meta[0] - minha_pos['quantidade']
            progresso = (minha_pos['quantidade'] / prox_meta[0]) * 100
            
            st.progress(progresso / 100)
            st.markdown(f"**Faltam {faltam} livros para desbloquear:** {prox_meta[1]}")
        else:
            st.success("🎉 Parabéns! Você desbloqueou todas as conquistas!")
            st.balloons()
    else:
        st.info(f"👤 **{operador_atual}**, você ainda não catalogou nenhum livro na competição.")
        st.markdown("**Comece agora e entre no ranking!** 🚀")
    
    st.markdown("---")
    
    # CONQUISTAS DISPONÍVEIS
    with st.expander("🏅 Todas as Conquistas Disponíveis", expanded=False):
        st.markdown("""
        ### Sistema de Conquistas
        
        Catalogue livros para desbloquear badges especiais:
        
        | Conquista | Requisito | Badge |
        |-----------|-----------|-------|
        | **Novato** | 5 livros | 🔰 |
        | **Iniciante** | 10 livros | 🌟 |
        | **Atirador** | 25 livros | 🎯 |
        | **Estrela** | 50 livros | ⭐ |
        | **Centenário** | 100 livros | 💯 |
        
        **Sequências:**
        - 🔥 Catalogue por 7 dias consecutivos = "Sequência de Fogo"
        - ⚡ Catalogue por 30 dias consecutivos = "Relâmpago"
        
        **Especiais:**
        - 👑 1º Lugar = "Líder Absoluto"
        - 🥇🥈🥉 Top 3 = Medalhas no pódio
        """)
    
    # METAS DA EQUIPE
    st.markdown("---")
    st.header("🎯 Meta da Equipe")
    
    # Definir metas
    meta_semanal = 100
    meta_mensal = 500
    
    # Calcular progresso
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    livros_semana = len(df_total[df_total['created_at'] >= pd.Timestamp(inicio_semana)])
    livros_mes = len(df_total[df_total['created_at'] >= pd.Timestamp(inicio_mes)])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Meta Semanal")
        progresso_semana = (livros_semana / meta_semanal) * 100
        st.progress(min(progresso_semana / 100, 1.0))
        st.markdown(f"**{livros_semana} / {meta_semanal} livros** ({progresso_semana:.1f}%)")
        
        if progresso_semana >= 100:
            st.success("🎉 Meta semanal alcançada! Parabéns equipe!")
        else:
            faltam_semana = meta_semanal - livros_semana
            st.info(f"Faltam {faltam_semana} livros para a meta semanal!")
    
    with col2:
        st.subheader("📆 Meta Mensal")
        progresso_mes = (livros_mes / meta_mensal) * 100
        st.progress(min(progresso_mes / 100, 1.0))
        st.markdown(f"**{livros_mes} / {meta_mensal} livros** ({progresso_mes:.1f}%)")
        
        if progresso_mes >= 100:
            st.success("🎊 Meta mensal alcançada! Equipe campeã!")
        else:
            faltam_mes = meta_mensal - livros_mes
            st.info(f"Faltam {faltam_mes} livros para a meta mensal!")

# Atualizar
st.markdown("---")
col1, col2 = st.columns([1, 3])

with col1:
    if st.button("🔄 Atualizar Ranking", use_container_width=True):
        get_ranking_data.clear()
        st.rerun()

with col2:
    st.caption(f"📊 Última atualização: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
    st.caption("💡 O ranking é atualizado em tempo real a cada minuto")

# Rodapé motivacional
st.markdown("---")
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; 
            border-radius: 10px; 
            text-align: center; 
            color: white;">
    <h3>💪 Continue catalogando e suba no ranking!</h3>
    <p>Cada livro conta. Cada esforço é valorizado. Juntos, construímos um acervo incrível!</p>
    <p style="font-size: 24px; margin-top: 10px;">🚀 Vamos lá, campeões! 🚀</p>
</div>
""", unsafe_allow_html=True)

