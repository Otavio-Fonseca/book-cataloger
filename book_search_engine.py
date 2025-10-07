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
    
    # ==================== BUSCA COM IA ====================
    
    def search_with_ai(self, title: str, author: str = None, isbn: str = None) -> Optional[Dict]:
        """
        Usa IA para encontrar dados do livro através de conhecimento do modelo
        
        A IA usa seu conhecimento treinado para fornecer informações sobre livros.
        Funciona melhor para livros conhecidos e populares.
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
            
            # Prompt melhorado e mais específico
            prompt = f"""Você é um bibliotecário especialista com acesso a informações sobre livros publicados.

TAREFA: Forneça informações PRECISAS sobre o seguinte livro:

{search_info}

INSTRUÇÕES IMPORTANTES:
1. Use seu conhecimento sobre livros para preencher os dados
2. Se o livro for conhecido, forneça informações precisas
3. Se NÃO conhecer o livro, retorne "N/A" nos campos desconhecidos
4. NÃO invente dados - apenas forneça o que você SABE
5. Para gênero, use termos em PORTUGUÊS (ex: Ficção, Romance, História, etc.)

FORMATO DE RESPOSTA (apenas JSON, sem texto adicional):
```json
{{
    "title": "título completo oficial do livro em português",
    "author": "nome completo do autor principal",
    "publisher": "nome da editora brasileira (se souber)",
    "genre": "gênero literário em português",
    "year": "ano de publicação",
    "isbn13": "ISBN-13 completo (13 dígitos)"
}}
```

IMPORTANTE: Retorne APENAS o JSON, sem explicações antes ou depois."""
            
            # Fazer chamada para OpenRouter
            session = requests.Session()
            session.headers.update({
                'Authorization': f'Bearer {config["api_key"]}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/book-cataloger',
                'X-Title': 'Book Cataloger'
            })
            
            model_name = config["model"].replace(" 🔍", "").strip()
            
            # Payload otimizado
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system", 
                        "content": "Você é um bibliotecário especialista. Forneça informações precisas sobre livros quando souber, ou 'N/A' quando não souber. Retorne sempre JSON válido sem markdown."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 600,
                "temperature": 0.1,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            # Adicionar response_format para modelos que suportam
            if 'gpt-4' in model_name or 'gpt-3.5' in model_name:
                payload["response_format"] = {"type": "json_object"}
            
            # Debug: Mostrar que está buscando
            with st.spinner(f"🤖 Consultando IA ({model_name})..."):
                response = session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    timeout=(10, 45)
                )
            
            # Debug: Mostrar status
            if response.status_code != 200:
                st.error(f"❌ Erro na API: {response.status_code}")
                st.error(f"Resposta: {response.text[:200]}")
                return None
            
            result_data = response.json()
            
            # Verificar se há erro na resposta
            if 'error' in result_data:
                st.error(f"❌ Erro do OpenRouter: {result_data['error']}")
                return None
            
            # Extrair conteúdo
            if 'choices' not in result_data or not result_data['choices']:
                st.error("❌ Resposta vazia da IA")
                return None
            
            content = result_data['choices'][0]['message']['content'].strip()
            
            # Debug: Mostrar resposta bruta (opcional)
            with st.expander("🔍 Debug: Resposta da IA", expanded=False):
                st.code(content)
            
            # Limpar markdown se presente
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Tentar parsear JSON
            try:
                book_data = json.loads(content)
            except json.JSONDecodeError as je:
                st.error(f"❌ Erro ao parsear JSON da IA: {je}")
                st.code(content)
                return None
            
            # Validar campos obrigatórios
            if not isinstance(book_data, dict):
                st.error("❌ IA não retornou um objeto JSON válido")
                return None
            
            # Mapear campos e adicionar fonte
            result = {
                'title': book_data.get('title', 'N/A'),
                'author': book_data.get('author', 'N/A'),
                'publisher': book_data.get('publisher', 'N/A'),
                'genre': book_data.get('genre', 'N/A'),
                'year': book_data.get('year', 'N/A'),
                'cover_url': None,  # IA não fornece URL
                'source': f'IA ({model_name})'
            }
            
            # Mostrar resultado
            st.success(f"✅ IA retornou dados! Modelo: {model_name}")
            
            return result
        
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

