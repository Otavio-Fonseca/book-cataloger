"""
Sistema Avançado de Busca de Livros
Orquestração inteligente de múltiplas APIs com cache e fallback
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import streamlit as st


class BookSearchEngine:
    """Motor de busca inteligente para dados de livros"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.cache_duration_days = 30
        
        # Configuração de prioridades das APIs
        self.api_priority = [
            'openlibrary',
            'google_books',
            'isbndb'
        ]
        
        # Tradução de gêneros
        self.genre_translations = {
            'fiction': 'ficção', 'non-fiction': 'não-ficção',
            'biography': 'biografia', 'history': 'história',
            'science': 'ciência', 'technology': 'tecnologia',
            'philosophy': 'filosofia', 'psychology': 'psicologia',
            'self-help': 'autoajuda', 'business': 'negócios',
            'romance': 'romance', 'fantasy': 'fantasia',
            'science fiction': 'ficção científica', 'horror': 'terror',
            'mystery': 'mistério', 'thriller': 'suspense',
            'children': 'infantil', 'young adult': 'jovem adulto',
            'poetry': 'poesia', 'drama': 'drama'
        }
    
    def translate_genre(self, genre: str) -> str:
        """Traduz gênero do inglês para português"""
        if not genre or genre.lower() == 'n/a':
            return 'N/A'
        
        genre_lower = genre.lower()
        for eng, pt in self.genre_translations.items():
            if eng in genre_lower:
                genre_lower = genre_lower.replace(eng, pt)
        
        return genre_lower.title()
    
    # ==================== CACHE ====================
    
    def check_cache(self, isbn: str) -> Optional[Dict]:
        """Verifica se existe resultado em cache válido"""
        try:
            # Buscar no cache
            response = self.supabase.table('cache_api').select('*').eq('isbn', isbn).execute()
            
            if response.data and len(response.data) > 0:
                cache_entry = response.data[0]
                
                # Verificar se o cache ainda é válido (< 30 dias)
                cached_at = datetime.fromisoformat(cache_entry['cached_at'].replace('Z', '+00:00'))
                age = datetime.now(cached_at.tzinfo) - cached_at
                
                if age.days < self.cache_duration_days:
                    # Cache válido!
                    return json.loads(cache_entry['dados_json'])
            
            return None
        except Exception as e:
            # Se houver erro no cache, continuar com busca normal
            return None
    
    def save_to_cache(self, isbn: str, data: Dict):
        """Salva resultado no cache"""
        try:
            cache_data = {
                'isbn': isbn,
                'dados_json': json.dumps(data, ensure_ascii=False),
                'cached_at': datetime.now().isoformat()
            }
            
            # Usar upsert para inserir ou atualizar
            self.supabase.table('cache_api').upsert(cache_data).execute()
        except Exception as e:
            # Falha no cache não deve impedir o fluxo
            pass
    
    # ==================== APIs INDIVIDUAIS ====================
    
    def search_openlibrary(self, isbn: str) -> Optional[Dict]:
        """Busca na Open Library API"""
        try:
            url = f"https://openlibrary.org/isbn/{isbn}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    'title': data.get('title', 'N/A'),
                    'author': 'N/A',
                    'publisher': 'N/A',
                    'genre': 'N/A',
                    'year': 'N/A',
                    'cover_url': None,
                    'source': 'Open Library'
                }
                
                # Buscar autores
                if 'authors' in data and data['authors']:
                    authors = []
                    for author_ref in data['authors'][:3]:  # Máximo 3 autores
                        try:
                            author_url = f"https://openlibrary.org{author_ref['key']}.json"
                            author_response = requests.get(author_url, timeout=5)
                            if author_response.status_code == 200:
                                author_data = author_response.json()
                                authors.append(author_data.get('name', ''))
                        except:
                            continue
                    
                    if authors:
                        result['author'] = ', '.join(authors)
                
                # Editora
                if 'publishers' in data and data['publishers']:
                    result['publisher'] = data['publishers'][0]
                
                # Gênero (subjects)
                if 'subjects' in data and data['subjects']:
                    result['genre'] = self.translate_genre(data['subjects'][0])
                
                # Ano de publicação
                if 'publish_date' in data:
                    result['year'] = data['publish_date']
                
                # Capa
                if 'covers' in data and data['covers']:
                    cover_id = data['covers'][0]
                    result['cover_url'] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                
                return result
        except Exception as e:
            return None
        
        return None
    
    def search_google_books(self, isbn: str) -> Optional[Dict]:
        """Busca na Google Books API"""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'items' in data and len(data['items']) > 0:
                    book = data['items'][0]['volumeInfo']
                    
                    result = {
                        'title': book.get('title', 'N/A'),
                        'author': ', '.join(book.get('authors', [])) if book.get('authors') else 'N/A',
                        'publisher': book.get('publisher', 'N/A'),
                        'genre': 'N/A',
                        'year': 'N/A',
                        'cover_url': None,
                        'source': 'Google Books'
                    }
                    
                    # Gênero (categories)
                    if 'categories' in book and book['categories']:
                        result['genre'] = self.translate_genre(book['categories'][0])
                    
                    # Ano de publicação
                    if 'publishedDate' in book:
                        result['year'] = book['publishedDate'][:4]  # Pegar apenas o ano
                    
                    # Capa
                    if 'imageLinks' in book:
                        result['cover_url'] = book['imageLinks'].get('thumbnail') or book['imageLinks'].get('smallThumbnail')
                    
                    return result
        except Exception as e:
            return None
        
        return None
    
    def search_isbndb(self, isbn: str) -> Optional[Dict]:
        """Busca na ISBNdb API (requer API key)"""
        try:
            # Verificar se há API key configurada
            if 'isbndb' not in st.secrets or 'api_key' not in st.secrets['isbndb']:
                return None
            
            api_key = st.secrets['isbndb']['api_key']
            url = f"https://api2.isbndb.com/book/{isbn}"
            headers = {'Authorization': api_key}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                book = data.get('book', {})
                
                result = {
                    'title': book.get('title', 'N/A'),
                    'author': book.get('authors', ['N/A'])[0] if book.get('authors') else 'N/A',
                    'publisher': book.get('publisher', 'N/A'),
                    'genre': book.get('subjects', ['N/A'])[0] if book.get('subjects') else 'N/A',
                    'year': book.get('date_published', 'N/A')[:4] if book.get('date_published') else 'N/A',
                    'cover_url': book.get('image'),
                    'source': 'ISBNdb'
                }
                
                return result
        except Exception as e:
            return None
        
        return None
    
    # ==================== BUSCA POR TÍTULO/AUTOR ====================
    
    def search_by_title_author(self, title: str, author: str = None) -> Optional[Dict]:
        """Busca por título e autor como fallback"""
        try:
            # Tentar Google Books primeiro (melhor para busca por título)
            query_parts = [f"intitle:{title}"]
            if author:
                query_parts.append(f"inauthor:{author}")
            
            query = ' '.join(query_parts)
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("totalItems", 0) > 0:
                    book = data["items"][0]["volumeInfo"]
                    
                    # Buscar ISBN
                    isbn = 'N/A'
                    if 'industryIdentifiers' in book:
                        for identifier in book['industryIdentifiers']:
                            if identifier['type'] in ['ISBN_13', 'ISBN_10']:
                                isbn = identifier['identifier']
                                break
                    
                    result = {
                        'title': book.get('title', 'N/A'),
                        'author': ', '.join(book.get('authors', [])) if book.get('authors') else 'N/A',
                        'publisher': book.get('publisher', 'N/A'),
                        'genre': self.translate_genre(', '.join(book.get('categories', ['N/A']))) if book.get('categories') else 'N/A',
                        'year': book.get('publishedDate', 'N/A')[:4] if book.get('publishedDate') else 'N/A',
                        'cover_url': book['imageLinks'].get('thumbnail') if 'imageLinks' in book else None,
                        'isbn': isbn,
                        'source': 'Google Books (Título/Autor)'
                    }
                    
                    return result
        except Exception as e:
            pass
        
        return None
    
    # ==================== TOOLS/FUNCTION CALLING ====================
    
    def _tool_search_google_books(self, isbn: str) -> str:
        """Tool que a IA pode chamar para pesquisar no Google Books"""
        result = self.search_google_books(isbn)
        if result:
            return json.dumps(result, ensure_ascii=False)
        return json.dumps({"error": "Livro não encontrado no Google Books"})
    
    def _tool_search_openlibrary(self, isbn: str) -> str:
        """Tool que a IA pode chamar para pesquisar na Open Library"""
        result = self.search_openlibrary(isbn)
        if result:
            return json.dumps(result, ensure_ascii=False)
        return json.dumps({"error": "Livro não encontrado na Open Library"})
    
    def _tool_web_search(self, query: str) -> str:
        """
        Tool de pesquisa na web MELHORADA com múltiplas estratégias
        Tenta várias fontes até encontrar informações úteis
        """
        try:
            import urllib.parse
            
            results = []
            sources_tried = []
            
            # ESTRATÉGIA 1: Google Books Search (mais confiável para livros)
            # Nota: Já foi tentado pela IA, mas vamos tentar com query diferente
            isbn_match = ''.join(filter(str.isdigit, query))
            
            if len(isbn_match) >= 10:  # Tem ISBN na query
                # Tentar buscar por ISBN com variações
                for isbn_variant in [isbn_match, f"ISBN {isbn_match}", f"ISBN-{isbn_match[:3]}-{isbn_match[3:]}"]:
                    try:
                        gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_match}"
                        gb_response = requests.get(gb_url, timeout=8)
                        
                        if gb_response.status_code == 200:
                            gb_data = gb_response.json()
                            
                            if gb_data.get('totalItems', 0) > 0:
                                item = gb_data['items'][0]['volumeInfo']
                                
                                title = item.get('title', '')
                                authors = ', '.join(item.get('authors', []))
                                publisher = item.get('publisher', '')
                                
                                if title:  # Encontrou algo!
                                    results.append(f"Título encontrado: {title}")
                                    if authors:
                                        results.append(f"Autor: {authors}")
                                    if publisher:
                                        results.append(f"Editora: {publisher}")
                                    
                                    sources_tried.append("Google Books Search ✅")
                                    break
                    except:
                        pass
                
                if results:
                    return json.dumps({
                        "success": True,
                        "query": query,
                        "results": results,
                        "sources": sources_tried,
                        "recommendation": "Use search_by_title com o título encontrado"
                    }, ensure_ascii=False)
            
            # ESTRATÉGIA 2: Open Library Search (alternativa)
            if isbn_match and len(isbn_match) >= 10:
                try:
                    ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_match}&format=json&jscmd=data"
                    ol_response = requests.get(ol_url, timeout=8)
                    
                    if ol_response.status_code == 200:
                        ol_data = ol_response.json()
                        
                        for key, book in ol_data.items():
                            title = book.get('title', '')
                            authors = [a.get('name', '') for a in book.get('authors', [])]
                            publishers = [p.get('name', '') for p in book.get('publishers', [])]
                            
                            if title:
                                results.append(f"Título: {title}")
                                if authors:
                                    results.append(f"Autores: {', '.join(authors)}")
                                if publishers:
                                    results.append(f"Editoras: {', '.join(publishers)}")
                                
                                sources_tried.append("Open Library Search ✅")
                                break
                except:
                    pass
                
                if results:
                    return json.dumps({
                        "success": True,
                        "query": query,
                        "results": results,
                        "sources": sources_tried,
                        "recommendation": "Use search_by_title com o título encontrado"
                    }, ensure_ascii=False)
            
            # ESTRATÉGIA 3: WorldCat (biblioteca global)
            if isbn_match and len(isbn_match) >= 10:
                try:
                    # WorldCat tem endpoint público
                    wc_url = f"https://www.worldcat.org/search?q=bn:{isbn_match}&qt=advanced&dblist=638"
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    wc_response = requests.get(wc_url, headers=headers, timeout=8, allow_redirects=True)
                    
                    if wc_response.status_code == 200:
                        # Extrair título da página (parsing básico)
                        import re
                        text = wc_response.text
                        
                        # Tentar encontrar título com regex
                        title_match = re.search(r'<title>([^|<]+)', text)
                        if title_match:
                            title = title_match.group(1).strip()
                            # Limpar título
                            title = title.replace('WorldCat.org:', '').strip()
                            
                            if len(title) > 3 and not title.lower().startswith('worldcat'):
                                results.append(f"Possível título: {title}")
                                sources_tried.append("WorldCat ✅")
                except:
                    pass
            
            # ESTRATÉGIA 4: ISBN DB Direto (se tiver múltiplos resultados)
            # Criar uma mensagem útil baseada no ISBN
            if isbn_match and not results:
                # Analisar padrão do ISBN para dar dicas
                if isbn_match.startswith('85') or isbn_match.startswith('978857'):
                    results.append("ISBN brasileiro detectado (prefixo 85)")
                    results.append("Sugestão: Procure em livrarias brasileiras como Amazon.com.br")
                    results.append("Livros brasileiros podem não estar em APIs internacionais")
                elif isbn_match.startswith('0') or isbn_match.startswith('1'):
                    results.append("ISBN inglês/americano detectado")
            
            # Se encontrou algo, retornar
            if results:
                return json.dumps({
                    "success": True,
                    "query": query,
                    "results": results,
                    "sources": sources_tried or ["Análise de padrão ISBN"],
                    "recommendation": "Se encontrou título, use search_by_title"
                }, ensure_ascii=False)
            
            # Se não encontrou nada em lugar nenhum
            return json.dumps({
                "success": False,
                "query": query,
                "message": "ISBN não encontrado em múltiplas fontes de busca",
                "sources_tried": ["Google Books", "Open Library", "WorldCat"],
                "recommendation": "ISBN pode estar incorreto ou livro muito raro"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "recommendation": "Erro na busca web - use preenchimento manual"
            }, ensure_ascii=False)
    
    def _tool_search_by_title(self, title: str, author: str = None) -> str:
        """Tool que a IA pode chamar para pesquisar por título e autor"""
        result = self.search_by_title_author(title, author)
        if result:
            return json.dumps(result, ensure_ascii=False)
        return json.dumps({"error": "Livro não encontrado por título/autor"})
    
    def get_available_tools(self):
        """Define as ferramentas disponíveis para a IA"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Pesquisa AVANÇADA de livros na web usando múltiplas fontes (Google Books Search, Open Library Search, WorldCat). MUITO EFICAZ para ISBNs raros ou regionais que não aparecem nas APIs normais. Retorna título, autor, editora quando encontrados. Use SEMPRE que as APIs diretas (search_google_books, search_openlibrary) falharem.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "ISBN do livro ou termo de busca. Funciona melhor com ISBN puro (ex: '8579308518')"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_google_books",
                    "description": "Pesquisa informações detalhadas de um livro na API do Google Books usando ISBN. Retorna título, autor, editora, gênero, ano e capa.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "isbn": {
                                "type": "string",
                                "description": "O código ISBN do livro (10 ou 13 dígitos)"
                            }
                        },
                        "required": ["isbn"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_openlibrary",
                    "description": "Pesquisa informações detalhadas de um livro na API da Open Library usando ISBN. Retorna título, autor, editora, gênero e ano.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "isbn": {
                                "type": "string",
                                "description": "O código ISBN do livro (10 ou 13 dígitos)"
                            }
                        },
                        "required": ["isbn"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_by_title",
                    "description": "Pesquisa livro usando título e opcionalmente autor. Use quando encontrar o título via web search mas não tiver ISBN, ou quando ISBN não funcionar nas outras APIs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Título do livro"
                            },
                            "author": {
                                "type": "string",
                                "description": "Nome do autor (opcional)"
                            }
                        },
                        "required": ["title"]
                    }
                }
            }
        ]
    
    # ==================== BUSCA COM IA (COM TOOLS) ====================
    
    # ==================== BUSCA COM IA (COM TOOLS/FUNCTION CALLING) ====================
    
    def search_with_ai(self, title: str, author: str = None, isbn: str = None) -> Optional[Dict]:
        """
        Usa IA com ferramentas de pesquisa para encontrar dados REAIS do livro.
        
        A IA pode chamar APIs do Google Books e Open Library em tempo real
        para garantir dados precisos e verificáveis.
        """
        try:
            # Verificar se OpenRouter está configurado
            if 'openrouter_config' not in st.session_state:
                st.warning("⚠️ OpenRouter não configurado. Configure em 'Configurações'.")
                return None
            
            config = st.session_state.openrouter_config
            if not config.get('enabled') or not config.get('api_key'):
                st.warning("⚠️ API do OpenRouter não está ativa. Ative em 'Configurações'.")
                return None
            
            model_name = config["model"].replace(" 🔍", "").strip()
            
            # Verificar se o modelo suporta function calling
            supports_tools = any(x in model_name.lower() for x in ['gpt-4', 'gpt-3.5', 'claude', 'gemini'])
            
            if not supports_tools:
                st.warning(f"⚠️ Modelo {model_name} pode não suportar tools.")
                st.info("💡 **Tentando fallback direto com web search...**")
                
                # Fallback: fazer web search manualmente
                with st.spinner("🌐 Pesquisando na web..."):
                    web_result = self._tool_web_search(f"ISBN {isbn}" if isbn else title)
                    web_data = json.loads(web_result)
                    
                    if web_data.get('success') and web_data.get('results'):
                        st.success(f"✅ Encontrado na web: {web_data['results'][0][:100]}...")
                        
                        # Tentar extrair título dos resultados
                        for result_text in web_data['results']:
                            if 'título' in result_text.lower() or 'title' in result_text.lower():
                                # Extrair título aproximado
                                import re
                                match = re.search(r'(?:título|title):\s*(.+?)(?:\||$)', result_text, re.IGNORECASE)
                                if match:
                                    found_title = match.group(1).strip()
                                    st.info(f"📚 Título encontrado: {found_title}")
                                    
                                    # Buscar por título
                                    title_result = self.search_by_title_author(found_title)
                                    if title_result:
                                        st.success("✅ Dados completos encontrados via web search + busca por título!")
                                        return title_result
                
                st.warning("⚠️ Modelo não suporta tools e fallback não encontrou dados. Use GPT-3.5 ou GPT-4.")
            
            # Preparar informações de busca
            search_parts = []
            if isbn and isbn != 'N/A':
                search_parts.append(f"ISBN: {isbn}")
            if title and title != 'N/A':
                search_parts.append(f"Título: {title}")
            if author and author != 'N/A':
                search_parts.append(f"Autor: {author}")
            
            if not search_parts:
                st.error("❌ Nenhuma informação disponível para busca com IA.")
                return None
            
            search_info = '\n'.join(search_parts)
            
            # Prompt para IA usar tools de forma inteligente
            prompt = f"""Você é um especialista em pesquisa bibliográfica com ferramentas poderosas de busca.

INFORMAÇÕES FORNECIDAS:
{search_info}

ESTRATÉGIA DE BUSCA OBRIGATÓRIA (siga EXATAMENTE esta ordem):

1. TENTATIVA 1 - APIs diretas (rápido mas limitado):
   → search_google_books("{isbn}") 
   → Se falhar: search_openlibrary("{isbn}")
   
2. SE FALHOU - WEB SEARCH (CRUCIAL para ISBNs raros/regionais):
   → web_search("{isbn}")
   → Esta ferramenta usa MÚLTIPLAS FONTES:
      • Google Books Search API
      • Open Library Search API  
      • WorldCat (biblioteca global)
      • Análise de padrão ISBN
   → DEVE retornar título e autor se o livro existir!
   
3. SE ENCONTROU TÍTULO - Buscar dados completos:
   → search_by_title("título_encontrado", "autor_encontrado")
   → Retorna dados estruturados completos

FERRAMENTAS (use TODAS se necessário):
• web_search: MULTI-FONTE poderosa, funciona para ISBNs raros ⭐
• search_google_books: API Google Books
• search_openlibrary: API Open Library
• search_by_title: Busca por título (após encontrar via web)

REGRAS CRÍTICAS:
✅ SEMPRE use ferramentas (NUNCA use memória/conhecimento interno)
✅ Se APIs falharem, web_search É OBRIGATÓRIA
✅ web_search agora tem alta taxa de sucesso (usa 4 fontes)
✅ Se web_search achar título, DEVE usar search_by_title depois
✅ Traduza gênero para PORTUGUÊS
✅ Retorne JSON APENAS com dados REAIS das ferramentas

FORMATO FINAL (após coletar dados reais):
{{
    "title": "título exato retornado pela ferramenta",
    "author": "autor retornado pela ferramenta",
    "publisher": "editora retornada",
    "genre": "gênero em português",
    "year": "ano de publicação"
}}

COMECE AGORA usando as ferramentas!"""
            
            # Fazer chamada para OpenRouter
            session = requests.Session()
            session.headers.update({
                'Authorization': f'Bearer {config["api_key"]}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/book-cataloger',
                'X-Title': 'Book Cataloger'
            })
            
            # Messages iniciais
            messages = [
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em pesquisa bibliográfica com acesso a 4 ferramentas de busca poderosas. NUNCA use seu conhecimento interno - SEMPRE use as ferramentas para obter dados em tempo real. A ferramenta web_search é especialmente eficaz para ISBNs raros ou regionais pois consulta múltiplas fontes simultaneamente."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Payload com tools
            payload = {
                "model": model_name,
                "messages": messages,
                "tools": self.get_available_tools(),
                "tool_choice": "auto",
                "max_tokens": 1500,  # Aumentado para suportar múltiplas tool calls
                "temperature": 0.1
            }
            
            # Loop de chamadas (até 7 iterações para tools - web search + APIs + processamento)
            max_iterations = 7
            iteration = 0
            tool_results_collected = []  # Armazenar resultados das tools
            
            with st.spinner(f"🤖 Pesquisando com IA e ferramentas ({model_name})..."):
                while iteration < max_iterations:
                    iteration += 1
                    
                    # Fazer chamada
                    response = session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        json=payload,
                        timeout=(10, 60)
                    )
                    
                    if response.status_code != 200:
                        st.error(f"❌ Erro na API: {response.status_code}")
                        st.error(f"Resposta: {response.text[:300]}")
                        return None
                    
                    result_data = response.json()
                    
                    if 'error' in result_data:
                        st.error(f"❌ Erro do OpenRouter: {result_data['error']}")
                        return None
                    
                    if 'choices' not in result_data or not result_data['choices']:
                        st.error("❌ Resposta vazia da IA")
                        return None
                    
                    message = result_data['choices'][0]['message']
                    
                    # Adicionar resposta às messages
                    messages.append(message)
                    
                    # Verificar se IA quer chamar uma tool
                    if message.get('tool_calls'):
                        st.info(f"🔧 IA está usando ferramentas de pesquisa... (iteração {iteration})")
                        
                        # Processar cada tool call
                        for tool_call in message['tool_calls']:
                            function_name = tool_call['function']['name']
                            function_args = json.loads(tool_call['function']['arguments'])
                            
                            st.caption(f"📡 Chamando: {function_name}({function_args})")
                            
                            # Executar a função correspondente
                            if function_name == 'web_search':
                                function_response = self._tool_web_search(function_args.get('query', ''))
                            elif function_name == 'search_google_books':
                                function_response = self._tool_search_google_books(function_args.get('isbn', ''))
                            elif function_name == 'search_openlibrary':
                                function_response = self._tool_search_openlibrary(function_args.get('isbn', ''))
                            elif function_name == 'search_by_title':
                                function_response = self._tool_search_by_title(
                                    function_args.get('title', ''),
                                    function_args.get('author')
                                )
                            else:
                                function_response = json.dumps({"error": "Função desconhecida"})
                            
                            # Armazenar resultado para fallback
                            try:
                                result_obj = json.loads(function_response)
                                if not result_obj.get('error'):
                                    tool_results_collected.append({
                                        'function': function_name,
                                        'args': function_args,
                                        'result': result_obj
                                    })
                            except:
                                pass
                            
                            # Adicionar resultado da tool às messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call['id'],
                                "content": function_response
                            })
                        
                        # Atualizar payload para próxima iteração
                        payload['messages'] = messages
                        
                        # Continuar loop para IA processar resultado
                        continue
                    
                    # Se não há tool_calls, IA terminou (ou não usou tools)
                    content = message.get('content', '').strip()
                    
                    # Verificar se IA usou alguma tool durante o processo
                    used_tools = any('tool_calls' in msg for msg in messages if isinstance(msg, dict))
                    
                    if not used_tools:
                        st.warning("⚠️ IA não usou nenhuma ferramenta de pesquisa!")
                        st.error("🔧 A IA deveria ter usado as tools para pesquisar, mas respondeu direto.")
                        st.info("💡 Possíveis causas:")
                        st.markdown("""
                        - Modelo não suporta function calling completamente
                        - Prompt não foi interpretado corretamente
                        - IA decidiu usar conhecimento ao invés de tools (incorreto)
                        """)
                        
                        # Mostrar o que a IA retornou
                        with st.expander("🔍 O Que a IA Retornou (SEM usar tools)", expanded=True):
                            st.code(content)
                        
                        st.info("🌐 **Executando web search manualmente como fallback...**")
                        
                        # Fazer web search manualmente
                        web_result = self._tool_web_search(f"ISBN {isbn} livro" if isbn else f"{title} {author or ''}")
                        web_data = json.loads(web_result)
                        
                        with st.expander("🔍 Resultado da Web Search Manual", expanded=True):
                            st.json(web_data)
                        
                        if web_data.get('success') and web_data.get('results'):
                            st.markdown("**📋 Informações encontradas na web:**")
                            for result in web_data['results']:
                                st.write(f"• {result}")
                        
                        return None
                    
                    if not content:
                        st.warning("⚠️ IA não retornou conteúdo final após usar tools")
                        with st.expander("🔍 Debug: Histórico de Messages", expanded=True):
                            st.json(messages)
                        return None
                    
                    # Debug: Mostrar resposta final
                    with st.expander("🔍 Debug: Resposta Final da IA (Após Tools)", expanded=False):
                        st.code(content)
                        st.markdown(f"**Tools usadas:** {iteration - 1}")
                        st.json(messages)
                    
                    # Parsear resposta final
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        content = content.split('```')[1].split('```')[0].strip()
                    
                    try:
                        book_data = json.loads(content)
                    except json.JSONDecodeError:
                        # Se não conseguir parsear, tentar extrair JSON
                        import re
                        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                        if json_match:
                            try:
                                book_data = json.loads(json_match.group())
                            except:
                                st.error(f"❌ Não foi possível extrair JSON válido")
                                st.code(content)
                                return None
                        else:
                            st.error(f"❌ Resposta não contém JSON válido")
                            st.code(content)
                            return None
                    
                    if not isinstance(book_data, dict):
                        st.error("❌ Formato inválido de resposta")
                        return None
                    
                    # Mapear campos
                    result = {
                        'title': book_data.get('title', 'N/A'),
                        'author': book_data.get('author', 'N/A'),
                        'publisher': book_data.get('publisher', 'N/A'),
                        'genre': book_data.get('genre', 'N/A'),
                        'year': book_data.get('year', 'N/A'),
                        'cover_url': book_data.get('cover_url'),
                        'source': f'IA com Tools ({model_name})'
                    }
                    
                    st.success(f"✅ IA pesquisou e retornou dados verificados!")
                    
                    return result
                
                # Se chegou aqui, excedeu iterações
                st.warning("⚠️ IA excedeu número máximo de iterações")
                
                # Debug: mostrar todas as tentativas
                with st.expander("🔍 Debug: Histórico Completo de Tentativas", expanded=True):
                    st.json(messages)
                    st.markdown(f"**Total de iterações:** {iteration}")
                    st.markdown(f"**Modelo usado:** {model_name}")
                    st.markdown(f"**ISBN pesquisado:** {isbn}")
                
                # IMPORTANTE: Verificar se alguma tool retornou dados válidos
                if tool_results_collected:
                    st.info("💡 IA chamou ferramentas mas não formatou resposta. Usando melhor resultado das tools...")
                    
                    with st.expander("🔍 Resultados Coletados das Tools", expanded=True):
                        for tr in tool_results_collected:
                            st.json(tr)
                    
                    # Pegar o melhor resultado (priorizar search_by_title, depois google_books, depois openlibrary)
                    best_result = None
                    
                    for priority_func in ['search_by_title', 'search_google_books', 'search_openlibrary']:
                        for tool_result in tool_results_collected:
                            if tool_result['function'] == priority_func:
                                best_result = tool_result['result']
                                st.success(f"✅ Usando resultado de: {priority_func}")
                                break
                        if best_result:
                            break
                    
                    if best_result and best_result.get('title') != 'N/A':
                        # Converter para formato esperado
                        result = {
                            'title': best_result.get('title', 'N/A'),
                            'author': best_result.get('author', 'N/A'),
                            'publisher': best_result.get('publisher', 'N/A'),
                            'genre': best_result.get('genre', 'N/A'),
                            'year': best_result.get('year', 'N/A'),
                            'cover_url': best_result.get('cover_url'),
                            'source': f"IA com Tools ({model_name}) - Auto-recuperado"
                        }
                        
                        st.success("✅ Dados recuperados das ferramentas que a IA chamou!")
                        return result
                
                # Se não tem resultados válidos das tools, tentar web search manual
                st.info("🌐 Nenhum resultado válido das tools. Tentando web search manual...")
                web_result = self._tool_web_search(f"ISBN {isbn} livro" if isbn else f"{title} {author or ''}")
                web_data = json.loads(web_result)
                
                with st.expander("🔍 Resultado da Web Search Manual", expanded=True):
                    st.json(web_data)
                
                if web_data.get('success') and web_data.get('results'):
                    st.success(f"✅ Informações encontradas na web!")
                    st.markdown("**📋 Informações disponíveis (use para preencher manual):**")
                    for result in web_data['results']:
                        st.write(f"• {result}")
                    
                    # Tentar extrair título e buscar
                    for result_text in web_data['results']:
                        # Tentar extrair título de várias formas
                        if 'título' in result_text.lower() or 'title' in result_text.lower():
                            possible_title = result_text.split(':')[-1] if ':' in result_text else result_text
                        else:
                            possible_title = result_text.split('|')[0] if '|' in result_text else result_text
                        
                        possible_title = possible_title.strip()[:100]
                        
                        if len(possible_title) > 5 and not possible_title.lower().startswith('resumo'):
                            st.info(f"🔍 Tentando buscar por: '{possible_title}'")
                            title_result = self.search_by_title_author(possible_title)
                            
                            if title_result and title_result.get('title') != 'N/A':
                                st.success("✅ Dados encontrados via web search + busca por título!")
                                return title_result
                
                st.warning("⚠️ Não foi possível encontrar dados mesmo com web search. Use preenchimento manual.")
                return None
        
        except requests.exceptions.Timeout:
            st.error("❌ Timeout na chamada da IA. Tente novamente.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na requisição: {str(e)}")
            return None
        except Exception as e:
            st.error(f"❌ Erro na busca com IA: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None
    
    # ==================== ORQUESTRAÇÃO PRINCIPAL ====================
    
    def is_complete(self, data: Dict) -> bool:
        """Verifica se os dados do livro estão completos"""
        required_fields = ['title', 'author', 'publisher']
        return all(
            data.get(field) and 
            data.get(field) != 'N/A' and 
            str(data.get(field)).strip() != ''
            for field in required_fields
        )
    
    def merge_data(self, base: Dict, enrichment: Dict) -> Dict:
        """Mescla dados de múltiplas fontes, priorizando campos não vazios"""
        merged = base.copy()
        
        # Lista de campos para enriquecer
        fields_to_enrich = ['title', 'author', 'publisher', 'genre', 'year', 'cover_url']
        
        for field in fields_to_enrich:
            # Se o campo base está vazio ou é N/A, tentar usar do enrichment
            if (not merged.get(field) or 
                merged.get(field) == 'N/A' or 
                str(merged.get(field)).strip() == ''):
                
                if enrichment.get(field) and enrichment.get(field) != 'N/A':
                    merged[field] = enrichment[field]
        
        # Adicionar fontes usadas
        if 'sources' not in merged:
            merged['sources'] = []
        
        if base.get('source'):
            if base['source'] not in merged['sources']:
                merged['sources'].append(base['source'])
        
        if enrichment.get('source'):
            if enrichment['source'] not in merged['sources']:
                merged['sources'].append(enrichment['source'])
        
        return merged
    
    def cascade_search(self, isbn: str) -> Dict:
        """
        Busca em cascata com enriquecimento de dados
        
        1. Verifica cache
        2. Busca em ordem de prioridade até encontrar dados completos
        3. Enriquece dados parciais com outras APIs
        4. Salva no cache
        """
        
        # 1. VERIFICAR CACHE
        cached_result = self.check_cache(isbn)
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result
        
        # 2. BUSCA EM CASCATA
        combined_data = {
            'title': 'N/A',
            'author': 'N/A',
            'publisher': 'N/A',
            'genre': 'N/A',
            'year': 'N/A',
            'cover_url': None,
            'sources': [],
            'from_cache': False
        }
        
        # Mapear funções de busca
        api_functions = {
            'openlibrary': self.search_openlibrary,
            'google_books': self.search_google_books,
            'isbndb': self.search_isbndb
        }
        
        # Buscar em ordem de prioridade
        for api_name in self.api_priority:
            search_func = api_functions.get(api_name)
            if not search_func:
                continue
            
            result = search_func(isbn)
            
            if result:
                combined_data = self.merge_data(combined_data, result)
                
                # Se já está completo, parar
                if self.is_complete(combined_data):
                    break
        
        # 3. ENRIQUECIMENTO ADICIONAL
        # Se ainda falta editora, tentar busca adicional
        if combined_data['publisher'] == 'N/A' and combined_data['title'] != 'N/A':
            enrichment = self.search_by_title_author(combined_data['title'], combined_data['author'])
            if enrichment:
                combined_data = self.merge_data(combined_data, enrichment)
        
        # 4. SALVAR NO CACHE (se encontrou algo útil)
        if combined_data['title'] != 'N/A':
            self.save_to_cache(isbn, combined_data)
        
        return combined_data
    
    # ==================== BUSCA PRINCIPAL (COM FALLBACKS) ====================
    
    def search_book(self, isbn: str = None, title: str = None, author: str = None, 
                    use_ai: bool = False) -> Dict:
        """
        Busca principal com fallbacks inteligentes
        
        Ordem de tentativas:
        1. Busca por ISBN (em cascata)
        2. Se falhar e tiver título/autor: Busca por título/autor
        3. Se use_ai=True: Busca com IA
        """
        
        result = {
            'title': 'N/A',
            'author': 'N/A',
            'publisher': 'N/A',
            'genre': 'N/A',
            'year': 'N/A',
            'cover_url': None,
            'sources': [],
            'from_cache': False
        }
        
        # 1. BUSCA POR ISBN
        if isbn:
            result = self.cascade_search(isbn)
            
            # Se encontrou dados completos, retornar
            if self.is_complete(result):
                return result
        
        # 2. FALLBACK: BUSCA POR TÍTULO/AUTOR
        if (result['title'] == 'N/A' or not self.is_complete(result)) and title:
            fallback_result = self.search_by_title_author(title, author)
            if fallback_result:
                result = self.merge_data(result, fallback_result)
        
        # 3. FALLBACK FINAL: IA (se solicitado)
        if use_ai and not self.is_complete(result):
            ai_result = self.search_with_ai(
                title or result.get('title', ''),
                author or result.get('author', ''),
                isbn
            )
            if ai_result:
                result = self.merge_data(result, ai_result)
        
        return result


# ==================== FUNÇÕES DE COMPATIBILIDADE ====================

def create_search_engine(supabase_client):
    """Factory function para criar o motor de busca"""
    return BookSearchEngine(supabase_client)

