# 📝 Convenção de Nomes de Arquivos

## ✅ Por Que Evitamos Emojis nos Nomes de Arquivos?

### Problemas Potenciais com Emojis:

1. **🪟 Windows**
   - Problemas de codificação em alguns sistemas
   - Git Bash pode não lidar bem com emojis
   - Alguns editores antigos têm problemas

2. **🔄 Git e Controle de Versão**
   - Encoding diferente entre sistemas
   - Possíveis conflitos em merge
   - Problemas em logs e diffs

3. **🚀 Deploy e CI/CD**
   - Alguns pipelines falham com caracteres especiais
   - Problemas em Docker/containers
   - Incompatibilidade em sistemas Linux antigos

4. **💾 Sistemas de Arquivo**
   - Diferentes encodings (UTF-8, UTF-16, etc.)
   - Problemas em backups
   - Incompatibilidade entre SO

5. **🔧 Ferramentas de Desenvolvimento**
   - Alguns IDEs têm problemas
   - Linters e formatters podem falhar
   - Scripts de build podem quebrar

---

## ✨ Nossa Solução

### Nomes de Arquivos (Apenas ASCII):
```
pages/
├── 1_Editar_Livro.py          ✅ Seguro
├── 2_Gerenciar_Generos.py     ✅ Seguro  
└── 3_Dashboard_Gestor.py      ✅ Seguro
```

### Emojis nos Títulos (Via Streamlit):
```python
st.set_page_config(
    page_title="Editar Livro",
    page_icon="✍️",  # ✅ Emoji aparece aqui
    layout="wide"
)
```

---

## 🎯 Resultado

### No Sistema de Arquivos:
```
✅ 1_Editar_Livro.py          (ASCII seguro)
✅ 2_Gerenciar_Generos.py     (ASCII seguro)
✅ 3_Dashboard_Gestor.py      (ASCII seguro)
```

### Na Interface do Streamlit:
```
✍️ Editar Livro               (Com emoji)
📚 Gerenciar Gêneros           (Com emoji)
📊 Dashboard Gestor            (Com emoji)
```

---

## 📋 Regras de Nomenclatura

### ✅ PERMITIDO em Nomes de Arquivos:
- Letras (a-z, A-Z)
- Números (0-9)
- Underscore (_)
- Hífen (-)
- Ponto (.)

### ❌ EVITAR em Nomes de Arquivos:
- Emojis (😀, 📚, etc.)
- Caracteres acentuados (á, é, ñ, etc.)
- Espaços (usar _ ou -)
- Caracteres especiais (@, #, $, etc.)

### ✅ PERMITIDO em Configurações do Streamlit:
- Emojis em `page_title`
- Emojis em `page_icon`
- Emojis em `st.title()`, `st.header()`, etc.
- Qualquer caractere Unicode em strings Python

---

## 🔄 Como o Streamlit Multi-Página Funciona

### Ordem de Exibição:
1. O Streamlit lê os arquivos na pasta `pages/`
2. Ordena alfabeticamente
3. Remove prefixos numéricos (`1_`, `2_`, etc.) para exibição
4. Usa o `page_icon` e `page_title` do `st.set_page_config()`

### Exemplo:
```
Arquivo: 1_Editar_Livro.py
Config:  st.set_page_config(page_title="Editar", page_icon="✍️")
Sidebar: ✍️ Editar Livro
```

---

## 🎨 Melhor dos Dois Mundos

✅ **Compatibilidade Total:**
- Funciona em qualquer OS
- Sem problemas com Git
- Deploy sem erros
- Backups sem corrupção

✅ **Interface Bonita:**
- Emojis visíveis na UI
- Navegação intuitiva
- Visual profissional
- UX otimizada

---

## 📚 Referências

- [Streamlit Multi-Page Apps](https://docs.streamlit.io/library/get-started/multipage-apps)
- [File Naming Best Practices](https://en.wikipedia.org/wiki/Filename#Comparison_of_filename_limitations)
- [Git on Windows Issues](https://git-scm.com/book/en/v2/Appendix-A%3A-Git-in-Other-Environments-Git-in-PowerShell)

---

**✅ Decisão Final: Emojis na UI, ASCII nos Arquivos!**

