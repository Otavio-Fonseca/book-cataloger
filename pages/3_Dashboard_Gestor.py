import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Dashboard do Gestor",
    page_icon="📊",
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

# Funções auxiliares para métricas
@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_total_livros():
    """Retorna o total de livros catalogados"""
    try:
        response = supabase.table('livro').select('id', count='exact').execute()
        return response.count if response.count else 0
    except Exception as e:
        st.error(f"Erro ao contar livros: {e}")
        return 0

@st.cache_data(ttl=300)
def get_total_generos():
    """Retorna o total de gêneros únicos"""
    try:
        response = supabase.table('genero').select('id', count='exact').execute()
        return response.count if response.count else 0
    except Exception as e:
        st.error(f"Erro ao contar gêneros: {e}")
        return 0

@st.cache_data(ttl=60)  # Cache por 1 minuto (dados mais atualizados)
def get_livros_hoje():
    """Retorna o total de livros catalogados hoje"""
    try:
        hoje = datetime.now().date().isoformat()
        response = supabase.table('livro').select('id', count='exact').gte('created_at', hoje).execute()
        return response.count if response.count else 0
    except Exception as e:
        st.error(f"Erro ao contar livros de hoje: {e}")
        return 0

@st.cache_data(ttl=300)
def get_dados_livros():
    """Retorna todos os livros com informações de gênero"""
    try:
        response = supabase.table('livro').select("""
            id,
            codigo_barras,
            titulo,
            autor,
            editora,
            created_at,
            operador_nome,
            genero:genero-id(nome)
        """).execute()
        
        if response.data:
            # Processar dados
            processed_data = []
            for row in response.data:
                processed_row = {
                    'id': row.get('id'),
                    'codigo_barras': row.get('codigo_barras', 'N/A'),
                    'titulo': row.get('titulo', 'N/A'),
                    'autor': row.get('autor', 'N/A'),
                    'editora': row.get('editora', 'N/A'),
                    'created_at': row.get('created_at', ''),
                    'operador_nome': row.get('operador_nome', 'Não identificado'),
                    'genero': row.get('genero', {}).get('nome', 'N/A') if row.get('genero') else 'N/A'
                }
                processed_data.append(processed_row)
            
            df = pd.DataFrame(processed_data)
            
            # Converter created_at para datetime
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'])
            
            return df
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados dos livros: {e}")
        return pd.DataFrame()

# Interface principal
st.title("📊 Dashboard do Gestor")
st.markdown("### Visão geral do processo de catalogação")
st.markdown("---")

# KPIs principais
st.header("📈 Métricas Principais (KPIs)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_livros = get_total_livros()
    st.metric(
        label="📚 Total de Livros",
        value=f"{total_livros:,}".replace(',', '.'),
        help="Total de livros catalogados no sistema"
    )

with col2:
    total_generos = get_total_generos()
    st.metric(
        label="📖 Gêneros Únicos",
        value=total_generos,
        help="Quantidade de gêneros literários cadastrados"
    )

with col3:
    livros_hoje = get_livros_hoje()
    st.metric(
        label="📅 Catalogados Hoje",
        value=livros_hoje,
        help="Livros catalogados no dia de hoje"
    )

with col4:
    # Média diária (últimos 7 dias)
    df_livros = get_dados_livros()
    if not df_livros.empty and 'created_at' in df_livros.columns:
        sete_dias_atras = datetime.now() - timedelta(days=7)
        livros_7_dias = df_livros[df_livros['created_at'] >= sete_dias_atras]
        media_diaria = len(livros_7_dias) / 7
        st.metric(
            label="📊 Média Diária (7d)",
            value=f"{media_diaria:.1f}",
            help="Média de livros catalogados por dia nos últimos 7 dias"
        )
    else:
        st.metric(label="📊 Média Diária (7d)", value="0")

st.markdown("---")

# Carregar dados para os gráficos
df_livros = get_dados_livros()

if not df_livros.empty:
    # Gráfico 1: Produtividade por Operador
    st.header("👥 Produtividade por Operador")
    
    # Agrupar por operador
    produtividade = df_livros.groupby('operador_nome').size().reset_index(name='quantidade')
    produtividade = produtividade.sort_values('quantidade', ascending=False)
    
    if not produtividade.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de barras
            fig_operadores = px.bar(
                produtividade,
                x='operador_nome',
                y='quantidade',
                title='Quantidade de Livros Catalogados por Operador',
                labels={'operador_nome': 'Operador', 'quantidade': 'Quantidade de Livros'},
                color='quantidade',
                color_continuous_scale='Blues',
                text='quantidade'
            )
            
            fig_operadores.update_traces(textposition='outside')
            fig_operadores.update_layout(
                xaxis_title="Operador",
                yaxis_title="Quantidade de Livros",
                showlegend=False,
                height=400
            )
            
            st.plotly_chart(fig_operadores, use_container_width=True)
        
        with col2:
            st.markdown("#### 🏆 Top 5 Operadores")
            for idx, row in produtividade.head(5).iterrows():
                st.metric(
                    label=f"{row['operador_nome']}",
                    value=f"{row['quantidade']} livros"
                )
    else:
        st.info("Nenhum dado de operador disponível.")
    
    st.markdown("---")
    
    # Gráfico 2: Distribuição por Gênero
    st.header("📚 Distribuição por Gênero Literário")
    
    # Agrupar por gênero
    distribuicao_genero = df_livros.groupby('genero').size().reset_index(name='quantidade')
    distribuicao_genero = distribuicao_genero.sort_values('quantidade', ascending=False)
    
    if not distribuicao_genero.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de pizza
            fig_generos = px.pie(
                distribuicao_genero,
                values='quantidade',
                names='genero',
                title='Distribuição Percentual de Livros por Gênero',
                hole=0.4,  # Gráfico de donut
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            fig_generos.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Quantidade: %{value}<br>Percentual: %{percent}<extra></extra>'
            )
            
            fig_generos.update_layout(height=500)
            
            st.plotly_chart(fig_generos, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 Top Gêneros")
            for idx, row in distribuicao_genero.head(10).iterrows():
                percentual = (row['quantidade'] / distribuicao_genero['quantidade'].sum()) * 100
                st.metric(
                    label=row['genero'],
                    value=f"{row['quantidade']} livros",
                    delta=f"{percentual:.1f}%"
                )
    else:
        st.info("Nenhum dado de gênero disponível.")
    
    st.markdown("---")
    
    # Gráfico 3: Evolução Temporal
    st.header("📈 Evolução da Catalogação ao Longo do Tempo")
    
    if 'created_at' in df_livros.columns:
        # Agrupar por data
        df_livros['data'] = df_livros['created_at'].dt.date
        evolucao_temporal = df_livros.groupby('data').size().reset_index(name='quantidade')
        evolucao_temporal = evolucao_temporal.sort_values('data')
        
        # Adicionar coluna de acumulado
        evolucao_temporal['acumulado'] = evolucao_temporal['quantidade'].cumsum()
        
        # Gráfico de linha com área
        fig_temporal = go.Figure()
        
        # Linha de quantidade diária
        fig_temporal.add_trace(go.Scatter(
            x=evolucao_temporal['data'],
            y=evolucao_temporal['quantidade'],
            name='Livros por Dia',
            mode='lines+markers',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.3)'
        ))
        
        # Linha de acumulado
        fig_temporal.add_trace(go.Scatter(
            x=evolucao_temporal['data'],
            y=evolucao_temporal['acumulado'],
            name='Total Acumulado',
            mode='lines',
            line=dict(color='#ff7f0e', width=3, dash='dash'),
            yaxis='y2'
        ))
        
        fig_temporal.update_layout(
            title='Catalogação Diária e Total Acumulado',
            xaxis_title='Data',
            yaxis_title='Livros Catalogados por Dia',
            yaxis2=dict(
                title='Total Acumulado',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_temporal, use_container_width=True)
        
        # Estatísticas adicionais
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dia_mais_produtivo = evolucao_temporal.loc[evolucao_temporal['quantidade'].idxmax()]
            st.metric(
                label="📅 Dia Mais Produtivo",
                value=dia_mais_produtivo['data'].strftime('%d/%m/%Y'),
                delta=f"{dia_mais_produtivo['quantidade']} livros"
            )
        
        with col2:
            media_geral = evolucao_temporal['quantidade'].mean()
            st.metric(
                label="📊 Média Diária Geral",
                value=f"{media_geral:.1f} livros/dia"
            )
        
        with col3:
            total_dias = len(evolucao_temporal)
            st.metric(
                label="📆 Dias de Catalogação",
                value=f"{total_dias} dias"
            )
    
    st.markdown("---")
    
    # Tabela de Atividade Recente
    st.header("🕐 Atividade Recente")
    
    # Últimos 10 livros catalogados
    ultimos_livros = df_livros.nlargest(10, 'created_at')[
        ['titulo', 'autor', 'genero', 'operador_nome', 'created_at']
    ].copy()
    
    ultimos_livros.columns = ['Título', 'Autor', 'Gênero', 'Operador', 'Catalogado em']
    
    st.dataframe(
        ultimos_livros,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Título": st.column_config.TextColumn("Título", width="large"),
            "Autor": st.column_config.TextColumn("Autor", width="medium"),
            "Gênero": st.column_config.TextColumn("Gênero", width="small"),
            "Operador": st.column_config.TextColumn("Operador", width="medium"),
            "Catalogado em": st.column_config.DatetimeColumn(
                "Catalogado em",
                format="DD/MM/YYYY HH:mm:ss",
                width="medium"
            )
        }
    )
    
    st.markdown("---")
    
    # Análises Adicionais
    st.header("🔍 Análises Adicionais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top Autores
        st.subheader("✍️ Top 10 Autores Mais Catalogados")
        top_autores = df_livros.groupby('autor').size().reset_index(name='quantidade')
        top_autores = top_autores.sort_values('quantidade', ascending=False).head(10)
        
        fig_autores = px.bar(
            top_autores,
            x='quantidade',
            y='autor',
            orientation='h',
            title='',
            labels={'autor': 'Autor', 'quantidade': 'Quantidade'},
            color='quantidade',
            color_continuous_scale='Greens'
        )
        
        fig_autores.update_layout(
            showlegend=False,
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig_autores, use_container_width=True)
    
    with col2:
        # Top Editoras
        st.subheader("🏢 Top 10 Editoras Mais Catalogadas")
        top_editoras = df_livros.groupby('editora').size().reset_index(name='quantidade')
        top_editoras = top_editoras.sort_values('quantidade', ascending=False).head(10)
        
        fig_editoras = px.bar(
            top_editoras,
            x='quantidade',
            y='editora',
            orientation='h',
            title='',
            labels={'editora': 'Editora', 'quantidade': 'Quantidade'},
            color='quantidade',
            color_continuous_scale='Purples'
        )
        
        fig_editoras.update_layout(
            showlegend=False,
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig_editoras, use_container_width=True)
    
    st.markdown("---")
    
    # Exportar Relatório
    st.header("📥 Exportar Relatório")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV Completo
        csv = df_livros.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Baixar Dados Completos (CSV)",
            data=csv,
            file_name=f"relatorio_catalogacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    
    with col2:
        # Relatório de Produtividade
        relatorio_prod = produtividade.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="👥 Relatório por Operador (CSV)",
            data=relatorio_prod,
            file_name=f"produtividade_operadores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    
    with col3:
        # Relatório de Gêneros
        relatorio_generos = distribuicao_genero.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📚 Distribuição por Gênero (CSV)",
            data=relatorio_generos,
            file_name=f"distribuicao_generos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

else:
    st.info("📚 Nenhum livro catalogado ainda. Comece a catalogar na página principal!")

# Botão de atualizar
st.markdown("---")
if st.button("🔄 Atualizar Dashboard"):
    # Limpar todos os caches
    get_total_livros.clear()
    get_total_generos.clear()
    get_livros_hoje.clear()
    get_dados_livros.clear()
    st.rerun()

# Rodapé com informações
st.markdown("---")
st.caption(f"📊 Dashboard atualizado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
st.caption("💡 Os dados são atualizados automaticamente a cada 5 minutos")

