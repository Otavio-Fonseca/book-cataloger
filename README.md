# 📚 Sistema de Catalogação de Livros

Sistema completo de catalogação de livros desenvolvido com **Streamlit** e **Supabase**, com busca inteligente, cache otimizado e integração de IA.

## ✨ Funcionalidades Principais

- 📖 **Catalogação Rápida** - Busca automática em múltiplas APIs
- ✍️ **Edição em Tabela** - Edite múltiplos livros de uma vez
- 📚 **Gerenciamento de Gêneros** - CRUD completo
- 📊 **Dashboard Analítico** - Métricas e gráficos interativos
- 🤖 **Busca com IA** - Para livros raros ou difíceis
- ⚡ **Cache Inteligente** - 97% mais rápido em buscas repetidas
- 👥 **Multi-usuário** - Rastreamento por operador

## 🚀 Início Rápido

### 1. Pré-requisitos

- Conta no [Supabase](https://supabase.com)
- Conta no [Streamlit Cloud](https://streamlit.io/cloud)
- Conta no [OpenRouter](https://openrouter.ai) (opcional, para IA)

### 2. Deploy

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/book-cataloger.git
cd book-cataloger

# 2. Configure secrets no Streamlit Cloud
# Settings → Secrets → Adicione:
[supabase]
url = "https://seu-projeto.supabase.co"
key = "sua-service-role-key"

# 3. Crie a tabela de cache no Supabase
# SQL Editor → Cole docs/supabase_migrations.sql → Run

# 4. Deploy automático!
# Streamlit Cloud detecta e faz deploy
```

### 3. Pronto! 🎉

Acesse sua aplicação e comece a catalogar!

## 📂 Estrutura do Projeto

```
book-cataloger/
├── book_cataloger.py          # Página principal (catalogação)
├── book_search_engine.py      # Motor de busca avançado
├── utils_auth.py              # Sistema de autenticação
├── requirements.txt           # Dependências Python
├── packages.txt               # Dependências do sistema
├── README.md                  # Este arquivo
│
├── pages/                     # Páginas multi-página
│   ├── 1_Editar_Livro.py     # Edição em tabela
│   ├── 2_Gerenciar_Generos.py # CRUD de gêneros
│   └── 3_Dashboard_Gestor.py  # Analytics e relatórios
│
└── docs/                      # Documentação completa
    ├── INICIO_RAPIDO.md       # ⚡ Comece aqui!
    ├── SISTEMA_BUSCA_AVANCADO.md
    ├── DEPLOY_SISTEMA_BUSCA.md
    ├── GUIA_DE_USO.md
    ├── supabase_migrations.sql
    └── ... (outros documentos)
```

## 🎯 Funcionalidades

### 📖 Catalogação de Livros
- Busca automática em 3+ APIs (Open Library, Google Books, ISBNdb)
- Cache inteligente (30 dias)
- Busca com IA para livros raros
- Sugestão automática de gênero
- Detecção de duplicatas

### ✍️ Edição de Livros
- Visualização em tabela editável
- Edição inline (clique e edite)
- Múltiplas edições simultâneas
- Exclusão múltipla com confirmação
- Filtro automático por operador

### 📚 Gerenciamento de Gêneros
- CRUD completo (Create, Read, Update, Delete)
- Proteção contra exclusão de gêneros em uso
- Contagem de livros por gênero
- Exportação para CSV

### 📊 Dashboard do Gestor
- Métricas principais (KPIs)
- Gráficos de produtividade por operador
- Distribuição por gênero
- Evolução temporal
- Top autores e editoras
- Exportação de relatórios

## 🔧 Tecnologias

- **Frontend:** Streamlit
- **Backend:** Supabase (PostgreSQL)
- **APIs:** Open Library, Google Books, ISBNdb (opcional)
- **IA:** OpenRouter (Gemma3, GPT-4, Claude)
- **Gráficos:** Plotly
- **Cache:** Supabase + st.cache_data

## 📊 Performance

```
Busca (primeira vez):  2-3 segundos
Busca (cache):         0.1 segundos ⚡ (97% mais rápido!)
Taxa de sucesso:       90%+ (vs 60% antes)
Dados completos:       85% (vs 50% antes)
```

## 📖 Documentação

Toda documentação está na pasta `docs/`:

- **`INICIO_RAPIDO.md`** - Comece aqui (5 min)
- **`SISTEMA_BUSCA_AVANCADO.md`** - Documentação técnica
- **`DEPLOY_SISTEMA_BUSCA.md`** - Guia de deploy
- **`GUIA_DE_USO.md`** - Manual do usuário

## 🔐 Segurança

- Login obrigatório para todos os operadores
- Cada operador vê apenas seus próprios livros
- Campo "Operador" bloqueado (auditoria)
- Credenciais gerenciadas via Streamlit Secrets

## 🤝 Contribuindo

Este é um projeto em desenvolvimento ativo. Sugestões e melhorias são bem-vindas!

## 📄 Licença

Este projeto é de código aberto.

## 👤 Autor

Desenvolvido para otimização de catalogação de bibliotecas e acervos literários.

---

**🎉 Sistema completo e profissional de catalogação de livros!**

Para começar, leia: **`docs/INICIO_RAPIDO.md`**
