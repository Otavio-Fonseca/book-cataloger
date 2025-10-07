import streamlit as st
import cv2
import numpy as np
from pyzbar import pyzbar
# pytesseract removido - não é necessário para este sistema
from PIL import Image
import re
import requests
import os
from datetime import datetime
import pandas as pd
from difflib import SequenceMatcher
import unidecode
import socket
import subprocess
import openai
import json
import configparser
from supabase import create_client, Client
from utils_auth import check_login, get_operador_nome, show_user_info

# Inicializar cliente Supabase
try:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro ao conectar com o Supabase. Verifique os segredos do Streamlit.")
    st.code(e)
    st.stop()


# Configuração da página
st.set_page_config(
    page_title="Catalogação de Livros - Captura por Câmera",
    page_icon="📚",
    layout="wide"
)

# Funções para gerenciar configuração persistente
def load_config():
    """Carrega configurações do arquivo config.ini"""
    config = configparser.ConfigParser()
    config_file = "config.ini"
    
    if os.path.exists(config_file):
        config.read(config_file, encoding='utf-8')
        model = config.get("openrouter", "model", fallback="openai/gpt-3.5-turbo")
        # Adicionar emoji de volta se for um modelo que suporta tools
        if any(tool_model in model for tool_model in ["gemma", "gpt-4", "claude-3"]):
            model += " 🔍"
        return {
            "api_key": config.get("openrouter", "api_key", fallback=""),
            "model": model,
            "enabled": config.getboolean("openrouter", "enabled", fallback=False)
        }
    else:
        return {
            "api_key": "",
            "model": "openai/gpt-3.5-turbo",
            "enabled": False
        }

def save_config(api_key, model, enabled):
    """Salva configurações no arquivo config.ini"""
    config = configparser.ConfigParser()
    config_file = "config.ini"
    
    # Criar seção openrouter
    if not config.has_section("openrouter"):
        config.add_section("openrouter")
    
    # Remover emojis do nome do modelo antes de salvar
    clean_model = model.replace(" 🔍", "").strip()
    
    config.set("openrouter", "api_key", api_key)
    config.set("openrouter", "model", clean_model)
    config.set("openrouter", "enabled", str(enabled))
    
    # Salvar arquivo com codificação UTF-8
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)
    
    # Atualizar session_state
    st.session_state.openrouter_config = {
        "api_key": api_key,
        "model": model,  # Manter o modelo original com emoji no session_state
        "enabled": enabled
    }

# Funções auxiliares para otimização de pesquisa local
def similarity(a, b):
    """Calcula similaridade entre duas strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_text(text):
    """Normaliza texto removendo acentos e caracteres especiais"""
    if pd.isna(text) or text == "N/A":
        return ""
    return unidecode.unidecode(str(text).lower().strip())

def find_similar_books(query, field="title", threshold=0.6):
    """Encontra livros similares baseado em um campo específico"""
    df = load_catalog_data()
    if df.empty:
        return []
    
    # Mapear nomes de campos para colunas do DataFrame
    field_mapping = {
        "title": "Titulo",
        "author": "Autor", 
        "publisher": "Editora",
        "genre": "Genero",
        "barcode": "Codigo_Barras"
    }
    
    # Usar o nome correto da coluna
    actual_field = field_mapping.get(field, field)
    
    # Verificar se a coluna existe
    if actual_field not in df.columns:
        return []
    
    query_norm = normalize_text(query)
    similar_books = []
    
    for _, row in df.iterrows():
        field_value = normalize_text(row[actual_field])
        if field_value:
            sim = similarity(query_norm, field_value)
            if sim >= threshold:
                similar_books.append({
                    "similarity": sim,
                    "data": row.to_dict()
                })
    
    # Ordenar por similaridade
    similar_books.sort(key=lambda x: x["similarity"], reverse=True)
    return similar_books[:5]  # Retornar top 5

def get_autocomplete_suggestions(partial_text, field="title"):
    """Gera sugestões de auto-complete baseadas em texto parcial"""
    df = load_catalog_data()
    if df.empty or not partial_text:
        return []
    
    # Mapear nomes de campos para colunas do DataFrame
    field_mapping = {
        "title": "Titulo",
        "author": "Autor", 
        "publisher": "Editora",
        "genre": "Genero",
        "barcode": "Codigo_Barras"
    }
    
    # Usar o nome correto da coluna
    actual_field = field_mapping.get(field, field)
    
    # Verificar se a coluna existe
    if actual_field not in df.columns:
        return []
    
    partial_norm = normalize_text(partial_text)
    suggestions = []
    
    for _, row in df.iterrows():
        field_value = normalize_text(row[actual_field])
        if field_value and partial_norm in field_value:
            suggestions.append({
                "text": row[actual_field],
                "data": row.to_dict()
            })
    
    # Remover duplicatas e ordenar
    unique_suggestions = []
    seen = set()
    for suggestion in suggestions:
        if suggestion["text"] not in seen:
            unique_suggestions.append(suggestion)
            seen.add(suggestion["text"])
    
    return unique_suggestions[:10]  # Máximo 10 sugestões

def get_all_unique_values(field="title"):
    """Obtém todos os valores únicos de um campo para autocomplete"""
    df = load_catalog_data()
    if df.empty:
        return []
    
    # Mapear nomes de campos para colunas do DataFrame
    field_mapping = {
        "title": "Titulo",
        "author": "Autor", 
        "publisher": "Editora",
        "genre": "Genero",
        "barcode": "Codigo_Barras"
    }
    
    # Usar o nome correto da coluna
    actual_field = field_mapping.get(field, field)
    
    # Verificar se a coluna existe
    if actual_field not in df.columns:
        return []
    
    # Obter valores únicos não nulos
    unique_values = df[actual_field].dropna().unique().tolist()
    
    # Filtrar valores vazios e ordenar
    unique_values = [v for v in unique_values if v and str(v).strip() != ""]
    unique_values.sort()
    
    return unique_values[:50]  # Máximo 50 sugestões

def create_autocomplete_widget(field_name, field_key, current_value="", help_text=""):
    """Cria um widget de autocomplete para um campo específico"""
    # Garantir que current_value seja string
    current_value = str(current_value) if current_value else ""
    
    # Se há valor atual (dados da API), usar text_input para garantir preenchimento
    if current_value and current_value.strip():
        return st.text_input(
            f"{field_name} *:",
            value=current_value,
            help=f"{help_text} Campo obrigatório - Valor preenchido automaticamente."
        )
    
    # Se não há valor atual, usar selectbox com sugestões
    suggestions = get_all_unique_values(field_key)
    
    if suggestions:
        return st.selectbox(
            f"{field_name} *:",
            options=[""] + suggestions,
            help=f"{help_text} Sugestões baseadas em registros anteriores."
        )
    else:
        # Se não há sugestões, criar text_input normal
        return st.text_input(
            f"{field_name} *:",
            value=current_value,
            help=f"{help_text} Campo obrigatório."
        )

def get_local_ip():
    """Obtém o IP local da máquina"""
    try:
        # Conecta a um endereço externo para descobrir o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.1"  # Fallback

def scan_network_for_webcam():
    """Escaneia a rede local em busca de dispositivos com IP Webcam"""
    local_ip = get_local_ip()
    base_ip = ".".join(local_ip.split(".")[:-1])  # Remove último octeto
    
    st.info(f"🔍 Escaneando rede {base_ip}.x em busca de IP Webcam...")
    
    found_devices = []
    progress_bar = st.progress(0)
    
    # Escaneia IPs comuns
    common_ips = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250]
    
    for i, ip_num in enumerate(common_ips):
        ip = f"{base_ip}.{ip_num}"
        progress_bar.progress((i + 1) / len(common_ips))
        
        try:
            # Testa se o IP responde na porta 8080
            url = f"http://{ip}:8080/video"
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    found_devices.append({
                        "ip": ip,
                        "url": url,
                        "status": "✅ Ativo"
                    })
                cap.release()
        except:
            pass
    
    progress_bar.empty()
    return found_devices

# Funções de processamento de imagem (focadas apenas em código de barras)
def process_image_for_barcode(image):
    """Processa uma imagem para extrair apenas o código de barras"""
    # Converter para formato OpenCV
    if isinstance(image, Image.Image):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Detectar código de barras
    barcodes = pyzbar.decode(image)
    barcode_data = None
    
    if barcodes:
        for barcode in barcodes:
            barcode_data = barcode.data.decode("utf-8")
            break
    
    return barcode_data

def detect_barcode_from_frame(frame):
    """Detecta código de barras em um frame de vídeo"""
    try:
        # Converter para escala de cinza
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detectar códigos de barras
        barcodes = pyzbar.decode(gray)
        
        for barcode in barcodes:
            # Extrair dados do código de barras
            barcode_data = barcode.data.decode("utf-8")
            barcode_type = barcode.type
            
            # Desenhar retângulo ao redor do código de barras
            (x, y, w, h) = barcode.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Adicionar texto
            text = f"{barcode_type}: {barcode_data}"
            cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return barcode_data, frame
    except Exception as e:
        st.error(f"Erro na detecção de código de barras: {e}")
    
    return None, frame

# Funções de busca de dados (reutilizadas da versão anterior)
def translate_genre(genre):
    """Traduz gêneros do inglês para português"""
    translations = {
        'fiction': 'ficção',
        'non-fiction': 'não-ficção',
        'biography': 'biografia',
        'history': 'história',
        'science': 'ciência',
        'technology': 'tecnologia',
        'philosophy': 'filosofia',
        'psychology': 'psicologia',
        'applied': 'aplicada',
        'self-help': 'autoajuda',
        'business': 'negócios',
        'economics': 'economia',
        'politics': 'política',
        'religion': 'religião',
        'art': 'arte',
        'music': 'música',
        'literature': 'literatura',
        'poetry': 'poesia',
        'drama': 'drama',
        'mystery': 'mistério',
        'thriller': 'suspense',
        'romance': 'romance',
        'fantasy': 'fantasia',
        'science fiction': 'ficção científica',
        'horror': 'terror',
        'adventure': 'aventura',
        'children': 'infantil',
        'young adult': 'jovem adulto',
        'education': 'educação',
        'reference': 'referência',
        'cookbook': 'culinária',
        'health': 'saúde',
        'fitness': 'fitness',
        'travel': 'viagem',
        'guide': 'guia'
    }
    
    if not genre or genre.lower() == 'n/a':
        return 'N/A'
    
    genre_lower = genre.lower()
    for eng, pt in translations.items():
        if eng in genre_lower:
            genre_lower = genre_lower.replace(eng, pt)
    
    return genre_lower.title()

def search_openlibrary(barcode):
    """Busca dados na Open Library API usando o código de barras com coleta melhorada de editora"""
    try:
        url = f"https://openlibrary.org/isbn/{barcode}.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            title = data.get('title', 'N/A')
            
            # Buscar autores
            authors = []
            if 'authors' in data:
                for author_ref in data['authors']:
                    author_key = author_ref['key']
                    author_url = f"https://openlibrary.org{author_key}.json"
                    try:
                        author_response = requests.get(author_url, timeout=5)
                        if author_response.status_code == 200:
                            author_data = author_response.json()
                            authors.append(author_data.get('name', 'N/A'))
                    except:
                        continue
            
            author = ', '.join(authors) if authors else 'N/A'
            
            # Buscar editora com mais detalhes
            publisher = 'N/A'
            if 'publishers' in data and data['publishers']:
                # Tentar buscar detalhes da editora
                publisher_key = data['publishers'][0]['key']
                publisher_url = f"https://openlibrary.org{publisher_key}.json"
                try:
                    publisher_response = requests.get(publisher_url, timeout=5)
                    if publisher_response.status_code == 200:
                        publisher_data = publisher_response.json()
                        publisher = publisher_data.get('name', data['publishers'][0].get('name', 'N/A'))
                    else:
                        publisher = data['publishers'][0].get('name', 'N/A')
                except:
                    publisher = data['publishers'][0].get('name', 'N/A')
            
            # Buscar gênero (subjects)
            subjects = data.get('subjects', [])
            genre = subjects[0] if subjects else 'N/A'
            genre = translate_genre(genre)
            
            return {
                'title': title,
                'author': author,
                'publisher': publisher,
                'genre': genre,
                'source': 'Open Library'
            }
    except Exception as e:
        st.error(f"Erro ao buscar na Open Library: {e}")
    return None

def search_google_books(barcode):
    """Busca dados na Google Books API usando o código de barras"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{barcode}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                book = data['items'][0]['volumeInfo']
                
                title = book.get('title', 'N/A')
                authors = book.get('authors', [])
                author = ', '.join(authors) if authors else 'N/A'
                publisher = book.get('publisher', 'N/A')
                
                categories = book.get('categories', [])
                genre = categories[0] if categories else 'N/A'
                genre = translate_genre(genre)
                
                return {
                    'title': title,
                    'author': author,
                    'publisher': publisher,
                    'genre': genre,
                    'source': 'Google Books'
                }
    except Exception as e:
        st.error(f"Erro ao buscar no Google Books: {e}")
    return None

def search_google_books_by_title(title):
    """Busca dados na Google Books API usando o título"""
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{title}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("totalItems", 0) > 0:
                book = data["items"][0]["volumeInfo"]
                
                return {
                    "title": book.get("title", "N/A"),
                    "author": ", ".join(book.get("authors", ["N/A"])),
                    "publisher": book.get("publisher", "N/A"),
                    "genre": translate_genre(", ".join(book.get("categories", ["N/A"]))),
                    "source": "Google Books (Título)"
                }
    except Exception as e:
        st.error(f"Erro ao buscar no Google Books (Título): {e}")
    return None

def search_worldcat(barcode):
    """Busca dados na WorldCat API usando o código de barras"""
    try:
        # WorldCat OpenSearch API
        url = f"http://www.worldcat.org/webservices/catalog/content/{barcode}?wskey=YOUR_KEY&format=json"
        # Como não temos chave, vamos usar uma abordagem alternativa
        # Buscar via Open Library que tem integração com WorldCat
        return None
    except Exception as e:
        return None

def search_isbn_org(barcode):
    """Busca dados no ISBN.org usando o código de barras"""
    try:
        # ISBN.org não tem API pública, mas podemos tentar scraping básico
        # Por enquanto, retornamos None
        return None
    except Exception as e:
        return None

def search_goodreads(barcode):
    """Busca dados na Goodreads API usando o código de barras"""
    try:
        # Goodreads API requer chave, mas podemos tentar uma busca alternativa
        # Usar Open Library que tem dados do Goodreads
        return None
    except Exception as e:
        return None

def search_amazon_books(barcode):
    """Busca dados na Amazon usando o código de barras (via scraping limitado)"""
    try:
        # Amazon não permite scraping, mas podemos tentar via APIs de terceiros
        # Por enquanto, retornamos None
        return None
    except Exception as e:
        return None

def search_openlibrary_works(barcode):
    """Busca dados adicionais na Open Library via works"""
    try:
        # Primeiro buscar o ISBN
        url = f"https://openlibrary.org/isbn/{barcode}.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Buscar works para mais detalhes
            if 'works' in data and data['works']:
                work_key = data['works'][0]['key']
                work_url = f"https://openlibrary.org{work_key}.json"
                work_response = requests.get(work_url, timeout=10)
                
                if work_response.status_code == 200:
                    work_data = work_response.json()
                    
                    # Buscar editora mais detalhada
                    publisher = 'N/A'
                    if 'publishers' in work_data and work_data['publishers']:
                        publisher_key = work_data['publishers'][0]['key']
                        publisher_url = f"https://openlibrary.org{publisher_key}.json"
                        try:
                            publisher_response = requests.get(publisher_url, timeout=5)
                            if publisher_response.status_code == 200:
                                publisher_data = publisher_response.json()
                                publisher = publisher_data.get('name', 'N/A')
                        except:
                            publisher = work_data['publishers'][0].get('name', 'N/A')
                    
                    return {
                        'title': work_data.get('title', 'N/A'),
                        'publisher': publisher,
                        'source': 'Open Library Works'
                    }
    except Exception as e:
        return None
    return None

def search_local_catalog_first(barcode):
    """Busca primeiro no catálogo do Supabase, depois nas APIs se necessário"""
    try:
        # 1. PRIMEIRO: Verificar se já existe no banco de dados Supabase
        # Fazer SELECT com JOIN para pegar o nome do gênero
        # Para colunas com hífen, usamos a sintaxe: alias:coluna_foreign_key(campos)
        response = supabase.table('livro').select("""
            id,
            codigo_barras,
            titulo,
            autor,
            editora,
            genero:genero-id(nome)
        """).eq('codigo_barras', barcode).limit(1).execute()
        
        if response.data:
            livro_encontrado = response.data[0]
            # Retornar dados no formato esperado pelo resto do app
            return {
                'title': livro_encontrado.get('titulo', 'N/A'),
                'author': livro_encontrado.get('autor', 'N/A'),
                'publisher': livro_encontrado.get('editora', 'N/A'),
                'genre': livro_encontrado.get('genero', {}).get('nome', 'N/A') if livro_encontrado.get('genero') else 'N/A',
                'sources': ['catálogo_local'],
                'from_local': True
            }
        else:
            # 2. SEGUNDO: Se não existe localmente, buscar nas APIs
            return search_multiple_sources(barcode)
    except Exception as e:
        st.error(f"Erro ao buscar no catálogo local: {e}")
        # Em caso de erro, tentar buscar nas APIs
        return search_multiple_sources(barcode)

def search_multiple_sources(barcode):
    """Busca dados em múltiplas fontes usando o código de barras com coleta melhorada de editora"""
    # Fontes principais
    primary_sources = [search_openlibrary, search_google_books]
    # Fontes adicionais para editora
    additional_sources = [search_openlibrary_works]
    
    combined_data = {
        'title': 'N/A',
        'author': 'N/A',
        'publisher': 'N/A',
        'genre': 'N/A',
        'sources': [],
        'from_local': False
    }
    
    # Buscar nas fontes principais
    for search_func in primary_sources:
        result = search_func(barcode)
        if result:
            combined_data['sources'].append(result['source'])
            for key in ['title', 'author', 'publisher', 'genre']:
                if combined_data[key] == 'N/A' and result[key] != 'N/A':
                    combined_data[key] = result[key]
    
    # Se não encontrou editora, tentar fontes adicionais
    if combined_data['publisher'] == 'N/A':
        for search_func in additional_sources:
            result = search_func(barcode)
            if result and result.get('publisher', 'N/A') != 'N/A':
                combined_data['publisher'] = result['publisher']
                combined_data['sources'].append(result['source'])
                break
    
    # Se ainda não encontrou editora e tem título, tentar busca por título
    if combined_data['publisher'] == 'N/A' and combined_data['title'] != 'N/A':
        title_result = search_google_books_by_title(combined_data['title'])
        if title_result and title_result.get('publisher', 'N/A') != 'N/A':
            combined_data['publisher'] = title_result['publisher']
            combined_data['sources'].append(title_result['source'])
    
    return combined_data

# Funções auxiliares para gerenciamento de gêneros
def get_or_create_genero(nome_genero):
    """Busca um gênero pelo nome ou cria se não existir. Retorna o ID do gênero."""
    try:
        # Primeiro, tentar encontrar o gênero existente
        response = supabase.table('genero').select("id, nome").eq('nome', nome_genero).execute()
        
        if response.data and len(response.data) > 0:
            # Gênero já existe, retornar o ID
            return response.data[0]['id']
        else:
            # Gênero não existe, criar novo
            insert_response = supabase.table('genero').insert({'nome': nome_genero}).execute()
            if insert_response.data and len(insert_response.data) > 0:
                return insert_response.data[0]['id']
            else:
                st.error(f"Erro ao criar gênero '{nome_genero}'")
                return None
    except Exception as e:
        st.error(f"Erro ao buscar/criar gênero: {e}")
        return None

# Funções de otimização de pesquisa local
@st.cache_data(ttl=3600) # Cache por 1 hora
def load_catalog_data():
    """Carrega dados do catálogo do Supabase com JOIN na tabela genero"""
    try:
        # Fazer SELECT com JOIN para pegar o nome do gênero
        # Nota: O Supabase usa sintaxe especial para JOINs
        # Para colunas com hífen, usamos a sintaxe: alias:coluna_foreign_key(campos)
        response = supabase.table('livro').select("""
            id,
            codigo_barras,
            titulo,
            autor,
            editora,
            created_at,
            genero:genero-id(nome)
        """).execute()
        
        if response.data:
            # Processar os dados para formato esperado
            processed_data = []
            for row in response.data:
                processed_row = {
                    'Codigo_Barras': row.get('codigo_barras', 'N/A'),
                    'Titulo': row.get('titulo', 'N/A'),
                    'Autor': row.get('autor', 'N/A'),
                    'Editora': row.get('editora', 'N/A'),
                    'Genero': row.get('genero', {}).get('nome', 'N/A') if row.get('genero') else 'N/A',
                    'Data_Catalogacao': row.get('created_at', '')
                }
                processed_data.append(processed_row)
            
            # Converter para DataFrame
            df = pd.DataFrame(processed_data)
            return df
        else:
            return pd.DataFrame(columns=["Codigo_Barras", "Titulo", "Autor", "Editora", "Genero", "Data_Catalogacao"])
    except Exception as e:
        st.error(f"Erro ao carregar dados do catálogo: {e}")
        return pd.DataFrame(columns=["Codigo_Barras", "Titulo", "Autor", "Editora", "Genero", "Data_Catalogacao"])

def check_existing_records(barcode=None, title=None):
    """Verifica registros existentes no banco de dados Supabase"""
    df = load_catalog_data()
    matches = []
    
    try:
        if barcode:
            # Busca exata por código de barras
            exact_matches = df[df["Codigo_Barras"] == barcode]
            if not exact_matches.empty:
                for _, row in exact_matches.iterrows():
                    matches.append({
                        "tipo": "Código de Barras Exato",
                        "similaridade": 1.0,
                        "dados": row.to_dict()
                    })
        
        if title and not matches:
            # Busca por título similar
            title_norm = normalize_text(title)
            for _, row in df.iterrows():
                existing_title_norm = normalize_text(row["Titulo"])
                if existing_title_norm:
                    sim = similarity(title_norm, existing_title_norm)
                    if sim >= 0.8:  # 80% de similaridade
                        matches.append({
                            "tipo": "Título Similar",
                            "similaridade": sim,
                            "dados": row.to_dict()
                        })
        
        # Ordenar por similaridade
        matches.sort(key=lambda x: x["similaridade"], reverse=True)
        return matches[:3]  # Retornar apenas os 3 melhores matches
        
    except Exception as e:
        st.error(f"Erro ao verificar registros existentes: {e}")
        return []

def save_to_csv(data, quantity=1):
    """Salva um ou mais registros de livro no banco de dados Supabase"""
    try:
        # 1. Buscar ou criar o gênero e obter seu ID
        genero_id = get_or_create_genero(data['genre'])
        
        if genero_id is None:
            st.error("Não foi possível salvar: falha ao processar o gênero.")
            return False
        
        # 2. Obter nome do operador logado
        operador_nome = get_operador_nome()
        
        # 3. Prepara uma lista de dicionários para inserção
        # O campo 'created_at' é preenchido automaticamente pelo Supabase
        registros_para_inserir = []
        for _ in range(quantity):
            novo_registro = {
                'codigo_barras': data['barcode'],
                'titulo': data['title'],
                'autor': data['author'],
                'editora': data['publisher'],
                'genero-id': genero_id,
                'operador_nome': operador_nome
                # created_at será preenchido automaticamente
            }
            registros_para_inserir.append(novo_registro)

        # 4. Insere a lista de registros na tabela 'livro'
        response = supabase.table('livro').insert(registros_para_inserir).execute()

        # 5. Verificação de erro
        if not response.data:
            st.error("Falha ao salvar os dados no Supabase.")
            return False
        
        # 6. Invalida o cache após salvar
        load_catalog_data.clear()
        return True

    except Exception as e:
        st.error(f"Erro ao salvar no banco de dados: {e}")
        return False

# Opções de gêneros disponíveis
GENEROS_DISPONIVEIS = [
    "Poesia", "Literatura de Cordel", "Biografia", "Autobiografia", "Diálogo",
    "Hábito", "Psicologia", "Cultura Afro-brasileira", "História", "Teatro",
    "Educação", "Romance", "Ficção", "Fantasia", "Mitologia", "Literatura Infantil",
    "Adolescentes", "Infantojuvenil", "Suspense", "Lenda", "Folclore", "Novela",
    "Fábula", "Narrativa", "Afetividade", "Letramento", "Filosofia",
    "Política", "Culinária", "Crônica", "Conto", "Didatico"
]

def get_openrouter_config():
    """Obtém configuração do OpenRouter do arquivo config.ini"""
    if "openrouter_config" not in st.session_state:
        # Carregar configuração do arquivo
        config = load_config()
        st.session_state.openrouter_config = config
    return st.session_state.openrouter_config

def suggest_genre_with_llm(book_data):
    """Sugere gênero automaticamente para um livro usando LLM via OpenRouter"""
    config = get_openrouter_config()
    
    if not config["enabled"] or not config["api_key"]:
        return None
    
    try:
        # Usar requests diretamente para evitar problemas de proxy
        import requests
        import json
        
        # Configurar sessão com headers apropriados e configurações robustas
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json',
            'User-Agent': 'Book-Cataloger/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Configurar adapter com retry e timeout
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Preparar prompt para sugestão de gênero
        prompt = f"""
Analise o seguinte livro e sugira o gênero mais adequado:

Título: {book_data.get('title', 'N/A')}
Autor: {book_data.get('author', 'N/A')}
Editora: {book_data.get('publisher', 'N/A')}
Gênero atual: {book_data.get('genre', 'N/A')}

Gêneros disponíveis:
{', '.join(GENEROS_DISPONIVEIS)}

Considere:
- O título do livro
- O autor e sua obra conhecida
- A editora e seu perfil
- O gênero atual (se disponível)
- O contexto cultural brasileiro

Responda APENAS com o nome do gênero mais adequado, sem explicações adicionais.
"""
        
        # Preparar payload para OpenRouter
        # Remover emoji do nome do modelo
        model_name = config["model"].replace(" 🔍", "").strip()
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Você é um especialista em classificação de gêneros literários brasileiros. Analise os dados fornecidos e sugira o gênero mais adequado da lista fornecida."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.3
        }

        # Fazer chamada direta para OpenRouter com configurações robustas
        try:
            response = session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                timeout=(10, 30),  # (connect timeout, read timeout)
                verify=True,
                allow_redirects=True
            )
        except requests.exceptions.ConnectionError as e:
            st.error(f"❌ Erro de conexão: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            st.error(f"❌ Timeout na conexão: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na requisição: {str(e)}")
            return None
        
        if response.status_code == 200:
            result = response.json()
            genero_sugerido = result['choices'][0]['message']['content'].strip()
        else:
            st.error(f"Erro na API: {response.status_code} - {response.text}")
            return None
        
        # Verificar se o gênero está na lista
        if genero_sugerido in GENEROS_DISPONIVEIS:
            return genero_sugerido
        else:
            # Tentar encontrar o gênero mais similar
            from difflib import get_close_matches
            matches = get_close_matches(genero_sugerido, GENEROS_DISPONIVEIS, n=1, cutoff=0.6)
            if matches:
                return matches[0]
            else:
                return None  # Deixar em branco para preenchimento manual
            
    except Exception as e:
        st.error(f"Erro na sugestão automática de gênero: {str(e)}")
        return None

def search_additional_context(book_data):
    """Busca contexto adicional para melhorar a categorização"""
    try:
        # Buscar informações adicionais no Google Books
        title = book_data.get('title', '')
        author = book_data.get('author', '')
        
        if not title:
            return ""
        
        # Construir query de busca
        query = f"{title} {author}".strip()
        
        # Fazer busca no Google Books
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": query,
            "maxResults": 1,
            "langRestrict": "pt"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("items"):
                item = data["items"][0]
                volume_info = item.get("volumeInfo", {})
                
                # Extrair informações relevantes
                context_parts = []
                
                if volume_info.get("description"):
                    context_parts.append(f"Descrição: {volume_info['description'][:200]}...")
                
                if volume_info.get("categories"):
                    context_parts.append(f"Categorias: {', '.join(volume_info['categories'])}")
                
                if volume_info.get("subtitle"):
                    context_parts.append(f"Subtítulo: {volume_info['subtitle']}")
                
                return " | ".join(context_parts)
        
        return ""
        
    except Exception as e:
        return ""

# Interface principal
def main():
    # Verificar login antes de qualquer coisa
    if not check_login():
        st.stop()
    
    # Mostrar informações do usuário na sidebar
    show_user_info()
    
    st.title("📚 Catalogação de Livros - Código de Barras")
    st.markdown("---")
    
    # Inicializar variáveis de session_state
    if "from_autocomplete" not in st.session_state:
        st.session_state.from_autocomplete = False
    if "force_search" not in st.session_state:
        st.session_state.force_search = False
    if "codigo_barras" not in st.session_state:
        st.session_state.codigo_barras = None
    if "dados_livro" not in st.session_state:
        st.session_state.dados_livro = None
    if "sources_used" not in st.session_state:
        st.session_state.sources_used = []
    if "openrouter_config" not in st.session_state:
        st.session_state.openrouter_config = load_config()
    if "from_local" not in st.session_state:
        st.session_state.from_local = False
    
    # Sidebar para navegação (menu simplificado)
    with st.sidebar:
        st.header("📋 Opções")
        page = st.selectbox("Escolha uma opção:", [
            "📷 Catalogar Livros",
            "⚙️ Configurações"
        ])
    
    # Configurações do OpenRouter
    if page == "⚙️ Configurações":
        st.title("⚙️ Configurações do Sistema")
        st.markdown("---")
        
        config = get_openrouter_config()
        
        st.markdown("### 🤖 Sugestão Automática de Gênero")
        st.info("Configure a API do OpenRouter para sugestão automática de gêneros literários usando IA.")
        
        # Configuração da API
        with st.expander("🔑 Configuração da API OpenRouter", expanded=True):
            config["enabled"] = st.checkbox("Ativar sugestão automática de gênero", value=config["enabled"])
            
            if config["enabled"]:
                config["api_key"] = st.text_input(
                    "API Key do OpenRouter:", 
                    value=config["api_key"], 
                    type="password",
                    help="Obtenha sua API key em: https://openrouter.ai/keys"
                )
                
                # Seleção do modelo
                modelos_disponiveis = [
                    "openai/gpt-3.5-turbo",
                    "openai/gpt-4 🔍",
                    "openai/gpt-4-turbo 🔍",
                    "anthropic/claude-3-haiku",
                    "anthropic/claude-3-sonnet",
                    "google/gemini-pro",
                    "google/gemma-3-27b-it 🔍",
                    "meta-llama/llama-2-70b-chat",
                    "mistralai/mistral-7b-instruct"
                ]
                
                config["model"] = st.selectbox(
                    "Modelo de IA:",
                    modelos_disponiveis,
                    index=modelos_disponiveis.index(config["model"]) if config["model"] in modelos_disponiveis else 0,
                    help="Escolha o modelo de linguagem para sugestão de gênero. Modelos com 🔍 suportam tools de pesquisa."
                )
                
        # Mostrar informações sobre suporte a tools
        model_name = config["model"].replace(" 🔍", "").lower()
        if "gemma" in model_name or "gpt-4" in model_name:
            st.success("🔍 **Este modelo suporta tools de pesquisa!** O sistema pode buscar informações adicionais sobre livros para melhorar a precisão da classificação de gêneros.")
        else:
            st.info("ℹ️ Este modelo usa apenas os dados fornecidos para classificação de gêneros.")
        
        # Informações sobre configuração persistente
        with st.expander("💾 Configuração Persistente", expanded=True):
            st.markdown("""
            **Sistema de Configuração Automática:**
            - **💾 Salvar**: Salva suas credenciais no arquivo `config.ini`
            - **🔄 Carregar**: Carrega configurações salvas automaticamente
            - **🗑️ Limpar**: Remove configurações salvas
            
            **Vantagens:**
            - ✅ Não precisa inserir credenciais toda vez
            - ✅ Configurações persistem entre sessões
            - ✅ Arquivo `config.ini` fica no diretório do projeto
            - ✅ Seguro e local (não enviado para nuvem)
            
            **Como usar:**
            1. Configure sua API key e modelo
            2. Clique em "💾 Salvar Configuração"
            3. Na próxima vez, clique em "🔄 Carregar Configuração"
            """)
        
        # Mostrar fontes de consulta disponíveis
        with st.expander("📚 Fontes de Consulta Disponíveis"):
            st.markdown("""
            **Fontes Principais:**
            - **Open Library**: Base de dados livre com informações detalhadas de livros
            - **Google Books**: API do Google com metadados de livros
            
            **Fontes Adicionais para Editora:**
            - **Open Library Works**: Busca detalhada de editoras via works
            - **Google Books (Título)**: Busca por título como fallback
            
            **Fontes Futuras (requerem chaves de API):**
            - **WorldCat**: Catálogo mundial de bibliotecas
            - **Goodreads**: Rede social de livros
            - **ISBN.org**: Base oficial de ISBNs
            
            **Melhorias Implementadas:**
            - ✅ Coleta detalhada de editora via Open Library
            - ✅ Busca por título como fallback
            - ✅ Múltiplas tentativas de coleta de editora
            - ✅ Integração com works da Open Library
            """)
        
        # Botões de gerenciamento de configuração
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Salvar Configuração"):
                # Remover emoji do modelo antes de salvar
                clean_model = config["model"].replace(" 🔍", "").strip()
                save_config(config["api_key"], clean_model, config["enabled"])
                st.success("✅ Configuração salva com sucesso!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Carregar Configuração"):
                loaded_config = load_config()
                st.session_state.openrouter_config = loaded_config
                st.success("✅ Configuração carregada com sucesso!")
                st.rerun()
        
        with col3:
            if st.button("🗑️ Limpar Configuração"):
                if os.path.exists("config.ini"):
                    os.remove("config.ini")
                st.session_state.openrouter_config = {
                    "api_key": "",
                    "model": "openai/gpt-3.5-turbo",
                    "enabled": False
                }
                st.success("✅ Configuração limpa com sucesso!")
                st.rerun()
        
        st.markdown("---")
        
        # Teste da configuração
        if st.button("🧪 Testar Conexão"):
            if config["api_key"]:
                with st.spinner("Testando conexão..."):
                    try:
                        # Usar requests diretamente para evitar problemas de proxy
                        import requests
                        
                        # Configurar sessão com headers apropriados e configurações robustas
                        session = requests.Session()
                        session.headers.update({
                            'Authorization': f'Bearer {config["api_key"]}',
                            'Content-Type': 'application/json',
                            'User-Agent': 'Book-Cataloger/1.0',
                            'Accept': 'application/json',
                            'Connection': 'keep-alive'
                        })
                        
                        # Configurar adapter com retry e timeout
                        from requests.adapters import HTTPAdapter
                        from urllib3.util.retry import Retry
                        
                        retry_strategy = Retry(
                            total=3,
                            backoff_factor=1,
                            status_forcelist=[429, 500, 502, 503, 504],
                        )
                        adapter = HTTPAdapter(max_retries=retry_strategy)
                        session.mount("http://", adapter)
                        session.mount("https://", adapter)
                        
                        # Preparar payload para teste
                        # Remover emoji do nome do modelo
                        model_name = config["model"].replace(" 🔍", "").strip()
                        payload = {
                            "model": model_name,
                            "messages": [{"role": "user", "content": "Teste de conexão"}],
                            "max_tokens": 10,
                            "temperature": 0.3
                        }
                        
                        # Fazer chamada direta para OpenRouter com configurações robustas
                        try:
                            response = session.post(
                                "https://openrouter.ai/api/v1/chat/completions",
                                json=payload,
                                timeout=(10, 30),  # (connect timeout, read timeout)
                                verify=True,
                                allow_redirects=True
                            )
                        except requests.exceptions.ConnectionError as e:
                            st.error(f"❌ Erro de conexão: {str(e)}")
                            return
                        except requests.exceptions.Timeout as e:
                            st.error(f"❌ Timeout na conexão: {str(e)}")
                            return
                        except requests.exceptions.RequestException as e:
                            st.error(f"❌ Erro na requisição: {str(e)}")
                            return
                        
                        if response.status_code == 200:
                            st.success("✅ Conexão estabelecida com sucesso!")
                        else:
                            st.error(f"❌ Erro na API: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"❌ Erro na conexão: {str(e)}")
            else:
                st.warning("⚠️ Insira uma API key para testar a conexão.")
        
        # Gêneros disponíveis
        with st.expander("📋 Gêneros Disponíveis", expanded=False):
            st.markdown("**Gêneros que o sistema pode sugerir automaticamente:**")
            col1, col2 = st.columns(2)
            
            for i, genero in enumerate(GENEROS_DISPONIVEIS):
                if i % 2 == 0:
                    with col1:
                        st.write(f"• {genero}")
                else:
                    with col2:
                        st.write(f"• {genero}")
        
        # Instruções
        with st.expander("📖 Como Usar", expanded=False):
            st.markdown("""
            **Como funciona a sugestão automática de gênero:**
            
            1. **Configure a API**: Insira sua API key do OpenRouter
            2. **Escolha o modelo**: Selecione o modelo de IA desejado
            3. **Ative a funcionalidade**: Marque a opção de ativação
            4. **Use normalmente**: Ao catalogar livros, a sugestão será automática
            
            **Processo de sugestão:**
            - O sistema analisa título, autor, editora e gênero atual
            - Busca contexto adicional no Google Books
            - Usa IA para sugerir um dos gêneros disponíveis
            - Sugere o gênero mais adequado para revisão
            """)
        
        # Salvar configurações
        if st.button("💾 Salvar Configurações"):
            st.session_state.openrouter_config = config
            st.success("✅ Configurações salvas com sucesso!")
            st.rerun()
        
        return
    
    if page == "📷 Catalogar Livros":
        st.header("📷 Catalogação de Livros")
        
        # Input manual como método padrão
        st.subheader("🔍 Inserir Código de Barras")
        st.info("Digite o código de barras do livro para buscar suas informações automaticamente.")
        
        # Input manual - método padrão
        # Inicializar contador de sessão se não existir
        if "form_counter" not in st.session_state:
            st.session_state.form_counter = 0
        
        # Usar chave única baseada no contador para forçar limpeza do form
        form_key = f"manual_entry_form_{st.session_state.form_counter}"
        
        with st.form(form_key):
            # Mostrar mensagem de sucesso se acabou de salvar
            if st.session_state.get("just_saved", False):
                st.success("✅ Livro salvo com sucesso! Digite o próximo código de barras.")
                st.session_state.just_saved = False
            
            manual_barcode = st.text_input(
                "Código de Barras:", 
                placeholder="Digite o código de barras do livro",
                key=f"barcode_input_{st.session_state.form_counter}"
            )
            
            # Botões organizados: Buscar primeiro (recebe Enter do scanner), Limpar segundo
            col1, col2 = st.columns([2, 1])
            with col1:
                buscar_button = st.form_submit_button("🚀 Buscar Dados Online", type="primary")
            with col2:
                limpar_button = st.form_submit_button("🗑️ Limpar", help="Limpar o campo de código de barras")
            
            # Processar ações do formulário
            if buscar_button:
                if manual_barcode and manual_barcode.strip():
                    st.session_state.codigo_barras = manual_barcode.strip()
                    st.session_state.force_search = True
                    st.rerun()
                else:
                    st.warning("Por favor, digite um código de barras.")
            
            if limpar_button:
                # Limpar dados e incrementar contador para resetar form
                st.session_state.codigo_barras = None
                st.session_state.dados_livro = None
                st.session_state.sources_used = []
                st.session_state.from_autocomplete = False
                st.session_state.force_search = False
                st.session_state.from_local = False
                st.session_state.form_counter += 1
                st.rerun()
        
        
        # Processar código de barras se disponível
        if "codigo_barras" in st.session_state and st.session_state.codigo_barras:
            codigo_barras = st.session_state.codigo_barras
            st.subheader(f"Dados para o Código de Barras: {codigo_barras}")
            
            dados_livro = None
            from_local = False  # Inicializar variável
            
            if "dados_livro" in st.session_state and not st.session_state.force_search:
                dados_livro = st.session_state.dados_livro
                sources_used = st.session_state.sources_used
                from_autocomplete = st.session_state.from_autocomplete
                # Verificar se veio do catálogo local
                from_local = st.session_state.get("from_local", False)
            else:
                with st.spinner("Buscando dados do livro..."):
                    dados_livro = search_local_catalog_first(codigo_barras)
                    sources_used = dados_livro.pop("sources")
                    from_local = dados_livro.pop("from_local", False)
                    st.session_state.dados_livro = dados_livro
                    st.session_state.sources_used = sources_used
                    st.session_state.from_local = from_local
                    st.session_state.force_search = False
                    from_autocomplete = False
            
            if dados_livro and dados_livro["title"] != "N/A":
                if from_local:
                    st.success("✅ Dados do livro encontrados no catálogo local!")
                    st.info("📚 **Este livro já estava catalogado anteriormente.**")
                else:
                    st.success("✅ Dados do livro encontrados online!")
                if from_autocomplete:
                    st.info("Este livro já existe no catálogo (sugestão do autocomplete).")
                
                # Preview removido para interface mais limpa
                
                
                # Sugestão automática de gênero
                config = get_openrouter_config()
                if config["enabled"] and config["api_key"]:
                    with st.spinner("🤖 Sugerindo gênero automaticamente..."):
                        # Buscar contexto adicional
                        contexto_adicional = search_additional_context(dados_livro)
                        
                        # Preparar dados para sugestão
                        dados_para_sugestao = dados_livro.copy()
                        if contexto_adicional:
                            dados_para_sugestao["contexto_adicional"] = contexto_adicional
                        
                        # Sugerir gênero com IA
                        genero_sugerido = suggest_genre_with_llm(dados_para_sugestao)
                        
                        if genero_sugerido:
                            st.success(f"🎯 **Gênero sugerido pela IA:** {genero_sugerido}")
                            dados_livro["genero_sugerido"] = genero_sugerido
                            
                            # Mostrar contexto adicional se disponível
                            if contexto_adicional:
                                with st.expander("🔍 Contexto adicional encontrado", expanded=False):
                                    st.write(contexto_adicional)
                        else:
                            st.info("ℹ️ **IA não conseguiu sugerir gênero automaticamente.** Preencha manualmente no formulário abaixo.")
                
                # Autocomplete inteligente avançado
                st.markdown("### 🔍 Sugestões Inteligentes (Catálogo Local)")
                
                # Busca por código de barras exato
                exact_matches = check_existing_records(barcode=codigo_barras)
                if exact_matches:
                    st.success("🎯 **Código de barras já existe no catálogo!**")
                    for i, match in enumerate(exact_matches):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"📚 **{match['dados']['Titulo']}**")
                            st.write(f"✍️ Autor: {match['dados']['Autor']}")
                            st.write(f"🏢 Editora: {match['dados']['Editora']}")
                        with col2:
                            if st.button(f"➕ Adicionar Cópia", key=f"add_exact_{i}_{match['dados']['Codigo_Barras']}"):
                                save_to_csv(match["dados"], quantity=1)
                                st.success(f"Cópia adicionada!")
                                load_catalog_data.clear()
                                st.rerun()
                
                # Busca por título similar
                similar_books = find_similar_books(dados_livro["title"], "title", 0.7)
                if similar_books:
                    st.markdown("#### 📖 Livros com Títulos Similares:")
                    for i, book in enumerate(similar_books):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"📚 **{book['data']['Titulo']}** (Similaridade: {book['similarity']:.2f})")
                            st.write(f"✍️ Autor: {book['data']['Autor']}")
                        with col2:
                            if st.button(f"➕ Usar Dados", key=f"use_similar_title_{i}_{book['data']['Codigo_Barras']}"):
                                st.session_state.dados_livro = {
                                    "title": book['data']['Titulo'],
                                    "author": book['data']['Autor'],
                                    "publisher": book['data']['Editora'],
                                    "genre": book['data']['Genero']
                                }
                                st.rerun()
                
                # Busca por autor similar
                similar_authors = find_similar_books(dados_livro["author"], "Autor", 0.8)
                if similar_authors:
                    st.markdown("#### ✍️ Livros do Mesmo Autor:")
                    for i, book in enumerate(similar_authors[:3]):  # Mostrar apenas 3
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"📚 **{book['data']['Titulo']}**")
                            st.write(f"✍️ Autor: {book['data']['Autor']}")
                        with col2:
                            if st.button(f"➕ Usar Dados", key=f"use_author_{i}_{book['data']['Codigo_Barras']}"):
                                st.session_state.dados_livro = {
                                    "title": book['data']['Titulo'],
                                    "author": book['data']['Autor'],
                                    "publisher": book['data']['Editora'],
                                    "genre": book['data']['Genero']
                                }
                                st.rerun()
                
                if not exact_matches and not similar_books and not similar_authors:
                    st.info("Nenhum livro similar encontrado no catálogo local.")
                
                # Formulário editável para revisar e completar dados
                st.markdown("### 📝 Revisar e Editar Dados do Livro")
                st.info("Revise os dados encontrados e edite conforme necessário antes de salvar no catálogo.")
                st.markdown("**📋 Campos obrigatórios:** Título, Autor, Editora e Gênero | **Quantidade:** Valor padrão 1")
                
                with st.form("edit_book_data_form"):
                    col1, col2 = st.columns(2)
                
                    with col1:
                        st.markdown("#### 📚 Informações Básicas")
                        final_barcode = st.text_input("Código de Barras:", value=codigo_barras, disabled=True)
                        # Usar autocomplete baseado em registros anteriores
                        final_title = create_autocomplete_widget(
                            "Título", "title", 
                            dados_livro.get("title", ""), 
                            "Campo obrigatório"
                        )
                        final_author = create_autocomplete_widget(
                            "Autor", "author", 
                            dados_livro.get("author", ""), 
                            "Campo obrigatório"
                        )
                    
                    with col2:
                        st.markdown("#### 🏢 Detalhes Adicionais")
                        final_publisher = create_autocomplete_widget(
                            "Editora", "publisher", 
                            dados_livro.get("publisher", ""), 
                            "Campo obrigatório"
                        )
                        
                        # Campo de gênero com sugestão da IA e autocomplete
                        genero_atual = dados_livro.get("genero_sugerido", dados_livro.get("genre", ""))
                        
                        # Obter sugestões de gênero do catálogo local
                        genero_suggestions = get_all_unique_values("genre")
                        all_genres = list(set(GENEROS_DISPONIVEIS + genero_suggestions))
                        all_genres.sort()
                        
                        if genero_atual and genero_atual in all_genres:
                            index_genero = all_genres.index(genero_atual) + 1
                        else:
                            index_genero = 0  # Deixar em branco se não houver sugestão válida
                        
                        final_genre = st.selectbox(
                            "Gênero *:",
                            options=[""] + all_genres,
                            index=index_genero,
                            help="Campo obrigatório - Gênero sugerido pela IA e baseado em registros anteriores"
                        )
                        
                        quantity = st.number_input("Quantidade de Cópias:", min_value=1, value=1, step=1, help="Valor padrão: 1")
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        save_button = st.form_submit_button("💾 Salvar no Catálogo", type="primary")
                    with col2:
                        clear_button = st.form_submit_button("🗑️ Limpar Formulário")
                    with col3:
                        search_again_button = st.form_submit_button("🔍 Buscar Novamente")
                    
                    if save_button:
                        # Validar todos os campos obrigatórios
                        missing_fields = []
                        if not final_title.strip():
                            missing_fields.append("Título")
                        if not final_author.strip():
                            missing_fields.append("Autor")
                        if not final_publisher.strip():
                            missing_fields.append("Editora")
                        if not final_genre.strip():
                            missing_fields.append("Gênero")
                        
                        if missing_fields:
                            st.error(f"❌ **Campos obrigatórios não preenchidos:** {', '.join(missing_fields)}")
                            st.warning("⚠️ **Todos os campos marcados com * são obrigatórios!**")
                        else:
                            save_data = {
                                "barcode": final_barcode,
                                "title": final_title.strip(),
                                "author": final_author.strip(),
                                "publisher": final_publisher.strip(),
                                "genre": final_genre.strip()
                            }
                            save_to_csv(save_data, quantity)
                            st.success(f"✅ {quantity} cópia(s) de '{final_title}' adicionada(s) ao catálogo!")
                            st.balloons()
                            load_catalog_data.clear() # Invalida o cache
                            
                            # Limpar dados da sessão
                            for key in ["codigo_barras", "dados_livro", "sources_used", "from_autocomplete", "force_search", "fallback_title_input", "from_local"]:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            # Incrementar contador do form para resetar completamente
                            st.session_state.form_counter += 1
                            st.session_state.just_saved = True
                            st.rerun()
                    
                    elif clear_button:
                        # Limpar dados da sessão
                        for key in ["codigo_barras", "dados_livro", "sources_used", "from_autocomplete", "force_search", "fallback_title_input", "from_local"]:
                            if key in st.session_state:
                                del st.session_state[key]
                        # Incrementar contador para resetar form
                        st.session_state.form_counter += 1
                        st.rerun()
                    
                    elif search_again_button:
                        # Forçar nova busca
                        st.session_state.force_search = True
                        st.rerun()
            else:
                st.warning("⚠️ Não foi possível encontrar dados para este código de barras nas fontes online.")
                
                # Opção 1: Busca por título
                st.markdown("### 🔍 Opção 1: Buscar por Título")
                with st.form("fallback_title_search_form"):
                    fallback_title = st.text_input("Título do Livro:", value=st.session_state.get("fallback_title_input", ""))
                    st.session_state.fallback_title_input = fallback_title
                    if st.form_submit_button("🔍 Buscar por Título"):
                        if fallback_title:
                            with st.spinner("Buscando por título..."):
                                title_data = search_google_books_by_title(fallback_title)
                                if title_data:
                                    st.success("✅ Livro encontrado por título!")
                                    st.session_state.dados_livro = {
                                        "barcode": codigo_barras, # Mantém o barcode original
                                        "title": title_data["title"],
                                        "author": title_data["author"],
                                        "publisher": title_data["publisher"],
                                        "genre": title_data["genre"]
                                    }
                                    st.session_state.sources_used = ["Google Books (Título)"]
                                    st.session_state.from_autocomplete = False
                                    st.rerun()
                                else:
                                    st.error("❌ Não foi possível encontrar o livro por este título.")
                        else:
                            st.warning("Por favor, digite um título para buscar.")
                
                # Opção 2: Preenchimento manual completo
                st.markdown("### ✏️ Opção 2: Preenchimento Manual")
                st.info("Preencha manualmente os dados do livro que não foram encontrados online.")
                st.markdown("**📋 Campos obrigatórios:** Título, Autor, Editora e Gênero | **Quantidade:** Valor padrão 1")
                
                with st.form("manual_book_data_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 📚 Informações Básicas")
                        manual_barcode = st.text_input("Código de Barras:", value=codigo_barras, disabled=True)
                        # Usar autocomplete baseado em registros anteriores
                        manual_title = create_autocomplete_widget(
                            "Título", "title", 
                            "", 
                            "Campo obrigatório"
                        )
                        manual_author = create_autocomplete_widget(
                            "Autor", "author", 
                            "", 
                            "Campo obrigatório"
                        )
                    
                    with col2:
                        st.markdown("#### 🏢 Detalhes Adicionais")
                        manual_publisher = create_autocomplete_widget(
                            "Editora", "publisher", 
                            "", 
                            "Campo obrigatório"
                        )
                        
                        # Gênero com sugestões do catálogo local
                        genero_suggestions = get_all_unique_values("genre")
                        all_genres = list(set(GENEROS_DISPONIVEIS + genero_suggestions))
                        all_genres.sort()
                        
                        manual_genre = st.selectbox(
                            "Gênero *:",
                            options=[""] + all_genres,
                            help="Campo obrigatório - Selecione o gênero do livro (sugestões baseadas em registros anteriores)"
                        )
                        manual_quantity = st.number_input("Quantidade de Cópias:", min_value=1, value=1, step=1, help="Valor padrão: 1")
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        manual_save_button = st.form_submit_button("💾 Salvar no Catálogo", type="primary")
                    with col2:
                        manual_clear_button = st.form_submit_button("🗑️ Limpar Formulário")
                    with col3:
                        manual_search_button = st.form_submit_button("🔍 Buscar por Título")
                    
                    if manual_save_button:
                        # Validar todos os campos obrigatórios
                        missing_fields = []
                        if not manual_title.strip():
                            missing_fields.append("Título")
                        if not manual_author.strip():
                            missing_fields.append("Autor")
                        if not manual_publisher.strip():
                            missing_fields.append("Editora")
                        if not manual_genre.strip():
                            missing_fields.append("Gênero")
                        
                        if missing_fields:
                            st.error(f"❌ **Campos obrigatórios não preenchidos:** {', '.join(missing_fields)}")
                            st.warning("⚠️ **Todos os campos marcados com * são obrigatórios!**")
                        else:
                            save_data = {
                                "barcode": manual_barcode,
                                "title": manual_title.strip(),
                                "author": manual_author.strip(),
                                "publisher": manual_publisher.strip(),
                                "genre": manual_genre.strip()
                            }
                            save_to_csv(save_data, manual_quantity)
                            st.success(f"✅ {manual_quantity} cópia(s) de '{manual_title}' adicionada(s) ao catálogo!")
                            st.balloons()
                            load_catalog_data.clear() # Invalida o cache
                            
                            # Limpar dados da sessão
                            for key in ["codigo_barras", "dados_livro", "sources_used", "from_autocomplete", "force_search", "fallback_title_input", "from_local"]:
                                if key in st.session_state:
                                    del st.session_state[key]
                            
                            # Incrementar contador do form para resetar
                            st.session_state.form_counter += 1
                            st.session_state.just_saved = True
                            st.rerun()
                    
                    elif manual_clear_button:
                        # Limpar dados da sessão
                        for key in ["codigo_barras", "dados_livro", "sources_used", "from_autocomplete", "force_search", "fallback_title_input", "from_local"]:
                            if key in st.session_state:
                                del st.session_state[key]
                        # Incrementar contador do form
                        st.session_state.form_counter += 1
                        st.rerun()
                    
                    elif manual_search_button:
                        if manual_title:
                            with st.spinner("Buscando por título..."):
                                title_data = search_google_books_by_title(manual_title)
                                if title_data:
                                    st.success("✅ Livro encontrado por título!")
                                    st.session_state.dados_livro = {
                                        "barcode": codigo_barras,
                                        "title": title_data["title"],
                                        "author": title_data["author"],
                                        "publisher": title_data["publisher"],
                                        "genre": title_data["genre"]
                                    }
                                    st.session_state.sources_used = ["Google Books (Título)"]
                                    st.session_state.from_autocomplete = False
                                    st.rerun()
                                else:
                                    st.error("❌ Não foi possível encontrar o livro por este título.")
                        else:
                            st.warning("Por favor, digite um título para buscar.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Limpar Formulário"):
                    for key in ["codigo_barras", "dados_livro", "sources_used", "from_autocomplete", "force_search", "fallback_title_input", "from_local"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    # Incrementar contador do form
                    st.session_state.form_counter += 1
                    st.rerun()
    

if __name__ == "__main__":
    main()

