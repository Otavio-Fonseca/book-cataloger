# 📚 Guia de Uso - Sistema de Catalogação de Livros

## 🎯 Visão Geral

Este é um sistema completo de catalogação de livros desenvolvido com **Streamlit** e **Supabase**, permitindo que múltiplos operadores trabalhem simultaneamente em um catálogo centralizado na nuvem.

---

## 🏗️ Estrutura da Aplicação

### Páginas Disponíveis:

| Página | Ícone | Função | Usuários |
|--------|-------|--------|----------|
| **Catalogação de Livros** | 📖 | Adicionar novos livros ao catálogo | Operadores |
| **Editar Livro** | ✍️ | Editar ou excluir livros existentes | Operadores/Gestores |
| **Gerenciar Gêneros** | 📚 | CRUD completo de gêneros literários | Administradores |
| **Dashboard Gestor** | 📊 | Análises e relatórios do sistema | Gestores |

---

## 📖 Página 1: Catalogação de Livros

### Objetivo:
Adicionar novos livros ao catálogo de forma rápida e eficiente.

### Fluxo de Trabalho:

1. **Digite o código de barras** do livro
2. **Clique em "Buscar Dados Online"**
   - O sistema busca automaticamente em:
     - Catálogo local (se já existe)
     - Google Books API
     - Open Library API
3. **Revise os dados** preenchidos automaticamente
4. **Complete ou corrija** informações se necessário:
   - Título ⭐ (obrigatório)
   - Autor ⭐ (obrigatório)
   - Editora ⭐ (obrigatório)
   - Gênero ⭐ (obrigatório)
   - Quantidade de cópias
5. **Clique em "Salvar no Catálogo"**

### Recursos Especiais:

#### 🤖 Sugestão Automática de Gênero (Opcional)
Se configurado, a IA sugere o gênero mais adequado baseado em:
- Título do livro
- Autor
- Editora
- Contexto da obra

**Como configurar:**
1. Vá em "⚙️ Configurações" (na sidebar)
2. Insira sua API Key do OpenRouter
3. Escolha o modelo de IA
4. Ative a sugestão automática

#### 🔍 Autocomplete Inteligente
O sistema sugere valores baseados em livros já catalogados:
- Títulos similares
- Autores existentes
- Editoras conhecidas
- Gêneros mais usados

#### 🎯 Detecção de Duplicatas
Se o livro já existe:
- ✅ Alerta visual
- ✅ Opção de adicionar mais cópias
- ✅ Comparação com registros similares

### Atalhos de Produtividade:

- ✅ **Enter** no campo de código de barras → Busca automática
- ✅ Campo limpa automaticamente após salvar
- ✅ Foco retorna ao campo de código de barras

---

## ✍️ Página 2: Editar Livro

### Objetivo:
Corrigir erros ou atualizar informações de livros já catalogados.

### Como Editar um Livro:

1. **Buscar o Livro:**
   - Digite o **Título** ou **Código de Barras**
   - Escolha o tipo de busca
   - Clique em "🔍 Buscar"

2. **Selecionar para Edição:**
   - Encontre o livro nos resultados
   - Clique para expandir
   - Clique em "✏️ Carregar para Edição"

3. **Editar Dados:**
   - Formulário será preenchido automaticamente
   - Altere os campos necessários
   - Todos os campos são editáveis

4. **Salvar Alterações:**
   - Clique em "💾 Salvar Alterações"
   - Confirmação visual de sucesso

### Como Excluir um Livro:

1. **Carregar o livro** para edição (passos 1-2 acima)
2. **Clicar em "🗑️ Excluir Livro"**
3. **⚠️ ATENÇÃO:** Marcar a caixa de confirmação:
   - "✅ Sim, tenho certeza que quero excluir este livro permanentemente"
4. **Confirmar** a exclusão

### ⚠️ Avisos Importantes:

- ❌ **A exclusão é permanente e irreversível**
- ❌ **Não há como recuperar livros excluídos**
- ✅ Use com cautela e sempre confirme os dados antes de excluir

---

## 📚 Página 3: Gerenciar Gêneros

### Objetivo:
Manter a lista de gêneros literários organizada e atualizada.

### Adicionar Novo Gênero:

1. Digite o nome no campo "Nome do Novo Gênero"
2. Clique em "➕ Adicionar Gênero"
3. ✅ Confirmação visual de adição

**Validações:**
- ⚠️ Não permite gêneros duplicados
- ⚠️ Nome não pode ser vazio

### Editar Gênero Existente:

1. **Expandir** o gênero desejado na lista
2. **Alterar** o nome no campo de texto
3. **Clicar em "💾 Salvar"**
4. ✅ Atualização confirmada

### Excluir Gênero:

1. **Expandir** o gênero desejado
2. **Clicar em "🗑️ Excluir"**
3. **Confirmar** a exclusão

**⚠️ Proteções:**
- ❌ **Não é possível excluir gêneros em uso**
- 💡 Se houver livros usando o gênero, você verá:
  - Quantidade de livros afetados
  - Mensagem de erro explicativa
  - Sugestão para reatribuir os livros primeiro

### Visualização:

- **Lista com expanders:** Edição rápida
- **Tabela completa:** Visão geral
- **Contagem de livros:** Quantos livros usam cada gênero
- **Exportação CSV:** Download da lista completa

---

## 📊 Página 4: Dashboard do Gestor

### Objetivo:
Fornecer insights e análises sobre o processo de catalogação.

### Métricas Principais (KPIs):

```
┌─────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Total de Livros │ Gêneros Únicos   │ Catalogados Hoje │ Média Diária (7d)│
│     1,234       │       45         │        12        │      8.5         │
└─────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### Gráficos e Análises:

#### 1️⃣ **Produtividade por Operador**
- 📊 Gráfico de barras interativo
- 🏆 Top 5 operadores em destaque
- 📈 Comparação de desempenho

**Use para:**
- Avaliar produtividade individual
- Identificar operadores mais ativos
- Planejar treinamentos

#### 2️⃣ **Distribuição por Gênero**
- 🥧 Gráfico de pizza (donut)
- 📊 Percentuais por gênero
- 📚 Top 10 gêneros

**Use para:**
- Entender a composição do acervo
- Identificar lacunas no catálogo
- Planejar aquisições

#### 3️⃣ **Evolução Temporal**
- 📈 Gráfico de linha com área
- 📊 Catalogação diária + acumulado
- 📅 Dia mais produtivo
- 📊 Média diária geral

**Use para:**
- Acompanhar progresso ao longo do tempo
- Identificar padrões e tendências
- Avaliar metas de catalogação

#### 4️⃣ **Atividade Recente**
- 📋 Últimos 10 livros catalogados
- ⏰ Timestamp de cada catalogação
- 👤 Operador responsável

**Use para:**
- Monitoramento em tempo real
- Verificação de qualidade
- Auditoria de atividades

#### 5️⃣ **Análises Adicionais**
- ✍️ **Top 10 Autores:** Mais catalogados
- 🏢 **Top 10 Editoras:** Mais presentes

**Use para:**
- Identificar autores populares no acervo
- Conhecer principais editoras
- Análise de fornecedores

### Exportação de Relatórios:

Três tipos de relatórios disponíveis:

| Relatório | Conteúdo | Uso |
|-----------|----------|-----|
| **📊 Dados Completos** | Todos os livros com todas as informações | Backup, análise externa |
| **👥 Por Operador** | Produtividade de cada operador | Avaliação de desempenho |
| **📚 Por Gênero** | Distribuição de gêneros | Análise do acervo |

**Formato:** CSV (compatível com Excel, Google Sheets)

### Atualização de Dados:

- 🔄 **Automática:** A cada 5 minutos
- 🔄 **Manual:** Botão "Atualizar Dashboard"
- 📅 **Timestamp:** Exibido no rodapé

---

## 🎯 Cenários de Uso

### Cenário 1: Catalogação Rápida (Operador)

**Situação:** Preciso catalogar 50 livros rapidamente

**Fluxo:**
1. ✅ Página: **Catalogação de Livros**
2. ✅ Escanear código de barras
3. ✅ Sistema busca dados automaticamente
4. ✅ Revisar e salvar
5. ✅ Repetir (campo limpa automaticamente)

**Tempo médio:** 30-45 segundos por livro

---

### Cenário 2: Correção de Erro (Operador)

**Situação:** Um livro foi catalogado com o autor errado

**Fluxo:**
1. ✅ Página: **Editar Livro**
2. ✅ Buscar por título ou ISBN
3. ✅ Carregar para edição
4. ✅ Corrigir o campo "Autor"
5. ✅ Salvar alterações

**Tempo médio:** 1-2 minutos

---

### Cenário 3: Organização de Gêneros (Administrador)

**Situação:** Preciso padronizar os nomes dos gêneros

**Fluxo:**
1. ✅ Página: **Gerenciar Gêneros**
2. ✅ Visualizar lista completa
3. ✅ Identificar gêneros similares
4. ✅ Editar nomes para padronizar
5. ✅ Excluir duplicatas (se não estiverem em uso)

**Resultado:** Catálogo organizado e consistente

---

### Cenário 4: Relatório Mensal (Gestor)

**Situação:** Preciso gerar relatório mensal de catalogação

**Fluxo:**
1. ✅ Página: **Dashboard Gestor**
2. ✅ Verificar KPIs do mês
3. ✅ Analisar gráficos:
   - Produtividade por operador
   - Distribuição por gênero
   - Evolução temporal
4. ✅ Exportar relatórios em CSV
5. ✅ Usar os CSVs para criar apresentação

**Tempo médio:** 10-15 minutos

---

## 🔧 Configurações e Manutenção

### Secrets do Streamlit

**Localização:** Settings → Secrets no Streamlit Cloud

```toml
[supabase]
url = "https://xxxxx.supabase.co"
key = "eyJhbGci..."
```

**⚠️ NUNCA compartilhe essas credenciais!**

### OpenRouter (Opcional)

Para ativar sugestão de gênero com IA:

```toml
[openrouter]
api_key = "sk-or-v1-..."
```

**Como obter:**
1. Acesse https://openrouter.ai/
2. Crie uma conta
3. Gere uma API key
4. Adicione nos secrets

---

## 🐛 Solução de Problemas

### Problema: "Erro ao conectar com o Supabase"

**Solução:**
1. Verifique os secrets no Streamlit Cloud
2. Confirme que a URL está correta
3. Verifique que a key é a **service_role** (não a anon)
4. Teste a conexão no painel do Supabase

### Problema: "Não consigo excluir um gênero"

**Causa:** Existem livros usando esse gênero

**Solução:**
1. Vá em "Dashboard Gestor"
2. Identifique os livros usando o gênero
3. Vá em "Editar Livro"
4. Altere o gênero desses livros
5. Tente excluir novamente

### Problema: "Os gráficos não carregam"

**Solução:**
1. Verifique sua conexão com internet
2. Clique em "🔄 Atualizar Dashboard"
3. Limpe o cache do navegador
4. Recarregue a página

### Problema: "Busca não encontra livros"

**Possíveis causas:**
- Código de barras incorreto
- Livro não existe nas APIs públicas
- Erro de digitação no título

**Solução:**
- Tente buscar por título
- Use preenchimento manual
- Verifique o código de barras

---

## 📞 Suporte Técnico

### Logs e Debug

1. **Streamlit Cloud:**
   - Acesse o painel do app
   - Clique em "Logs"
   - Verifique erros recentes

2. **Supabase:**
   - Painel → Table Editor
   - Verifique os dados diretamente
   - Logs de queries em "API Logs"

### Contato

Para problemas técnicos:
1. Verifique este guia
2. Consulte o CHANGELOG.md
3. Verifique os logs
4. Entre em contato com o suporte

---

## 📚 Recursos Adicionais

### Documentação:
- [Streamlit Docs](https://docs.streamlit.io/)
- [Supabase Docs](https://supabase.com/docs)
- [Plotly Docs](https://plotly.com/python/)

### Tutoriais:
- Como criar gêneros personalizados
- Como interpretar o dashboard
- Boas práticas de catalogação

---

## ✅ Checklist de Implementação

- [ ] Criar projeto no Supabase
- [ ] Criar tabelas `livro` e `genero`
- [ ] Configurar secrets no Streamlit Cloud
- [ ] Fazer deploy da aplicação
- [ ] Testar conexão
- [ ] Cadastrar gêneros iniciais
- [ ] Treinar operadores
- [ ] Começar catalogação!

---

**🎉 Pronto para catalogar! Boa sorte com seu projeto!**

*Desenvolvido com ❤️ usando Streamlit + Supabase*

