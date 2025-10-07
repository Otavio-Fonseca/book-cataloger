# 🔧 Troubleshooting - Busca com IA Não Funciona

## 🐛 Problema: "IA Não Encontrou Dados"

Se você clicou em **"🤖 Buscar com IA"** e não funcionou, siga este guia:

---

## 🔍 Passo 1: Verifique as Mensagens

### **Mensagem A: "IA não usou nenhuma ferramenta de pesquisa!"**

**O que significa:**
- IA respondeu direto sem usar as tools
- Modelo pode não suportar function calling
- IA ignorou as instruções

**Solução:**
1. Vá em **Configurações**
2. Troque o modelo para:
   - ✅ **openai/gpt-3.5-turbo** (recomendado)
   - ✅ **openai/gpt-4-turbo**
   - ✅ **anthropic/claude-3-sonnet**
3. Salve configuração
4. Tente novamente

---

### **Mensagem B: "IA excedeu número máximo de iterações"**

**O que significa:**
- IA tentou usar tools mas não conseguiu
- APIs retornaram erro
- Livro realmente não existe

**Solução:**
1. Expanda "🔍 Debug: Histórico Completo"
2. Veja qual tool foi chamada
3. Veja o resultado de cada tool
4. Se web search encontrou algo, use manual

---

### **Mensagem C: "Modelo X pode não suportar tools"**

**O que significa:**
- Modelo selecionado não tem function calling
- Fallback manual será executado

**Solução:**
1. Sistema tenta web search automaticamente
2. Veja os resultados apresentados
3. Use informações para preencher manual
4. OU troque para modelo compatível

---

## 🎯 Passo 2: Verifique o Modelo

### **Modelos que FUNCIONAM com Tools:**

| Modelo | Suporte Tools | Recomendado |
|--------|---------------|-------------|
| openai/gpt-3.5-turbo | ✅ Excelente | ⭐⭐⭐ |
| openai/gpt-4-turbo | ✅ Excelente | ⭐⭐⭐ |
| openai/gpt-4 | ✅ Excelente | ⭐⭐ |
| anthropic/claude-3-sonnet | ✅ Muito Bom | ⭐⭐⭐ |
| anthropic/claude-3-haiku | ✅ Bom | ⭐⭐ |
| google/gemini-pro | ✅ Bom | ⭐⭐ |

### **Modelos que NÃO FUNCIONAM:**

| Modelo | Problema |
|--------|----------|
| meta-llama/* | Sem suporte tools |
| mistralai/* (alguns) | Suporte limitado |
| Modelos menores | Sem function calling |

**Troque para GPT-3.5 Turbo!** (Melhor custo-benefício)

---

## 📊 Passo 3: Interprete o Debug

### **Expanda os Expanders de Debug:**

#### **A. "Debug: Histórico Completo de Tentativas"**

Mostra todas as interações IA ↔ Sistema

**O que procurar:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Pesquise ISBN..."
    },
    {
      "role": "assistant",
      "tool_calls": [...]  ← DEVE TER ISTO!
    }
  ]
}
```

**Se NÃO tiver `tool_calls`:**
- IA não usou ferramentas
- Troque o modelo

**Se TIVER `tool_calls`:**
- Veja qual tool foi chamada
- Veja o resultado retornado
- Pode ser que API não tinha o livro

---

#### **B. "Resultado da Web Search Manual"**

```json
{
  "success": true,
  "results": [
    "Título: Nome do Livro",
    "Autor: Nome do Autor",
    ...
  ]
}
```

**Se success = true:**
- Web encontrou informações!
- Use para preencher manualmente

**Se success = false:**
- Livro realmente muito raro
- Não está na internet
- Use preenchimento 100% manual

---

## 💡 Passo 4: Soluções Alternativas

### **Opção 1: Web Search Manual**

```
1. Pegue o ISBN
2. Pesquise no Google: "ISBN XXXXXXXXX"
3. Encontre título do livro
4. Volte para aplicação
5. Use "Opção 1: Buscar por Título"
6. Digite o título encontrado
7. Sistema busca nas APIs por título
```

### **Opção 2: Preenchimento Manual**

```
1. Pesquise o livro externamente
2. Encontre: Título, Autor, Editora
3. Use "Opção 2: Preenchimento Manual"
4. Preencha todos os campos
5. Salve no catálogo
```

---

## 🧪 Teste de Diagnóstico

### **Execute este teste:**

```
1. Vá em Configurações
2. Selecione "openai/gpt-3.5-turbo"
3. Salve
4. Volte para Catalogação
5. Digite ISBN: 9780439708180 (Harry Potter US)
6. Clique "🤖 Buscar com IA"
7. Observe:
   🔧 "IA usando ferramentas..."
   📡 "Chamando: search_google_books..."
   ✅ "Dados verificados!"
```

**Se ESTE ISBN funcionar:**
- Sistema está OK
- Problema é ISBN específico (muito raro)

**Se NÃO funcionar:**
- Copie TODO o debug
- Me envie para análise

---

## 📋 Checklist de Verificação

Antes de reportar problema, verifique:

- [ ] OpenRouter está configurado?
- [ ] API key está correta?
- [ ] Modelo é GPT-3.5 ou GPT-4?
- [ ] Configuração está salva?
- [ ] Testou com ISBN popular primeiro?
- [ ] Leu mensagens de erro?
- [ ] Expandiu todos os debug expanders?
- [ ] Copiou mensagens para análise?

---

## 🎯 O Que Fazer Agora

### **Se busca com IA falhou:**

1. **Veja o debug expandido** (tem muita informação útil!)
2. **Copie as mensagens** que aparecem
3. **Veja o "Resultado da Web Search Manual"**
4. **Use as informações** apresentadas para preencher manual
5. **Me envie o debug** se precisar ajuda

### **Informações Úteis para Enviar:**

```
1. ISBN que tentou buscar
2. Modelo configurado
3. Mensagens de erro/warning
4. Conteúdo dos expanders de debug
5. Resultado da web search manual
```

---

## 💬 Exemplo de Debug para Enviar

```
ISBN pesquisado: 9788573261479
Modelo: openai/gpt-3.5-turbo

Mensagem:
⚠️ IA não usou nenhuma ferramenta de pesquisa!

Debug mostrou:
{
  "messages": [
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "{ ... }"
      // SEM tool_calls!
    }
  ]
}

Web Search Manual encontrou:
{
  "success": true,
  "results": [
    "Título: ABC",
    "Autor: XYZ"
  ]
}
```

**Com estas informações posso diagnosticar e corrigir!**

---

## 🚀 Deploy da Versão com Debug

```bash
git add book_search_engine.py book_cataloger.py docs/TROUBLESHOOTING_IA.md
git commit -m "feat: adiciona debug extensivo e fallback manual na busca com IA"
git push
```

---

## 📝 Próximo Teste

**Agora quando buscar com IA:**

1. ✅ Verá se IA usou tools
2. ✅ Verá resultado de cada tool
3. ✅ **Web search manual executará automaticamente** se IA falhar
4. ✅ Terá informações para preencher manual
5. ✅ Debug completo para análise

**Teste novamente e me envie o resultado do debug! 🔍**

