"""
================================================================================
INGEST.PY - Indexador de Documentos PDF (Versión Ollama)
================================================================================

Este script procesa los PDFs de guías médicas y los indexa en una base
de datos vectorial (ChromaDB) usando embeddings de Ollama.

DIFERENCIA CON ai_backend/ingest_knowledge.py:
- Este usa Ollama embeddings (nomic-embed-text) - requiere Ollama corriendo
- El otro usa HuggingFace embeddings (all-MiniLM-L6-v2) - corre sin servidor

PROCESO:
1. Escanea la carpeta 'data/' buscando PDFs
2. Extrae el texto de cada PDF con PyPDFLoader
3. Divide el texto en fragmentos (chunks) de 1000 caracteres
4. Genera embeddings con Ollama (nomic-embed-text)
5. Guarda los vectores en ChromaDB

USO:
    # Asegúrate de que Ollama esté corriendo primero
    ollama serve
    
    # Luego ejecuta el script
    python ingest.py

REQUISITOS:
    - Ollama corriendo en localhost:11434
    - Modelo nomic-embed-text descargado: ollama pull nomic-embed-text
    - PDFs en la carpeta 'data/'
================================================================================
"""

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings

# Configuración de rutas
DATA_FOLDER = "data"                  # Carpeta con los PDFs de guías médicas
DB_PATH = "ai_engine/vector_db"       # Donde se guardará la DB vectorial


def ingerir_documentos():
    """
    Procesa todos los PDFs y crea la base de datos vectorial.
    
    PASOS:
    1. Verificar que existe la carpeta data/
    2. Cargar todos los PDFs
    3. Dividir en fragmentos (chunking)
    4. Generar embeddings con Ollama
    5. Guardar en ChromaDB
    """
    print(f"📂 Escaneando carpeta: {DATA_FOLDER}...")
    
    documentos_totales = []
    
    # Verificar que existe la carpeta
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ ERROR: No existe la carpeta {DATA_FOLDER}")
        return

    # Filtrar solo archivos PDF
    archivos = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    
    if not archivos:
        print("⚠️ No encontré ningún PDF en la carpeta /data")
        return

    print(f"📚 Encontrados {len(archivos)} documentos.")

    # =========================================================================
    # PASO 1: CARGAR PDFs
    # =========================================================================
    for archivo in archivos:
        ruta_completa = os.path.join(DATA_FOLDER, archivo)
        try:
            loader = PyPDFLoader(ruta_completa)
            documentos_totales.extend(loader.load())
        except Exception as e:
            print(f"   ⚠️ Error leyendo {archivo}: {e}")

    # =========================================================================
    # PASO 2: CHUNKING (Troceado)
    # =========================================================================
    # Dividimos el texto en fragmentos de 1000 caracteres
    # con solapamiento de 100 caracteres para mantener contexto
    print("✂️ Dividiendo texto en fragmentos...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,     # Tamaño máximo de cada fragmento
        chunk_overlap=100    # Solapamiento entre fragmentos
    )
    splits = text_splitter.split_documents(documentos_totales)
    print(f"🧩 Total de fragmentos generados: {len(splits)}")

    # =========================================================================
    # PASO 3: GENERAR EMBEDDINGS Y GUARDAR
    # =========================================================================
    # Usamos nomic-embed-text de Ollama para generar los vectores
    # Este modelo es rápido y produce buenos embeddings multilingües
    print("💾 Guardando en memoria vectorial (Modo Turbo)...")
    Chroma.from_documents(
        documents=splits,
        embedding=OllamaEmbeddings(model="nomic-embed-text"),
        persist_directory=DB_PATH
    )
    print("✅ ¡Ingestión completada! Tu IA ha estudiado todos los PDFs.")


if __name__ == "__main__":
    ingerir_documentos()
