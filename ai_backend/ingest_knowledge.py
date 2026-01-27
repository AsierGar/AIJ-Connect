"""
================================================================================
INGEST_KNOWLEDGE.PY - Indexador de Guías Médicas (RAG)
================================================================================

Este script procesa los PDFs de guías médicas y fichas técnicas, los trocea
en fragmentos y los indexa en una base de datos vectorial (ChromaDB).

Esto permite que el sistema de validación médica pueda buscar información
relevante de forma semántica (por significado, no solo por palabras clave).

PROCESO:
1. Escanea la carpeta 'data/' buscando archivos PDF
2. Extrae el texto de cada PDF
3. Divide el texto en fragmentos (chunks) de 1000 caracteres
4. Genera embeddings (vectores) para cada fragmento
5. Guarda los vectores en ChromaDB para búsqueda rápida

USO:
    python ingest_knowledge.py

    Ejecutar cada vez que se añadan nuevas guías o fichas técnicas.

REQUISITOS:
    - PDFs en la carpeta 'data/'
    - Conexión a internet (para descargar modelo de embeddings la primera vez)
================================================================================
"""

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Configuración de rutas
DATA_FOLDER = "data"                      # Carpeta con los PDFs
DB_PATH = "ai_backend/vector_db"          # Donde se guardará la DB vectorial


def ingest_data():
    """
    Procesa todos los PDFs y crea la base de datos vectorial.
    
    PASOS:
    1. Cargar PDFs desde la carpeta data/
    2. Dividir en fragmentos (chunking)
    3. Generar embeddings con modelo local
    4. Guardar en ChromaDB
    """
    print(f"📂 Escaneando carpeta: {DATA_FOLDER}...")
    
    documentos = []
    
    # =========================================================================
    # PASO 1: CARGAR PDFs
    # =========================================================================
    for archivo in os.listdir(DATA_FOLDER):
        if archivo.endswith(".pdf"):
            ruta = os.path.join(DATA_FOLDER, archivo)
            print(f"   📖 Leyendo: {archivo}...")
            try:
                loader = PyPDFLoader(ruta)
                documentos.extend(loader.load())
            except Exception as e:
                print(f"   ❌ Error leyendo {archivo}: {e}")

    if not documentos:
        print("⚠️ No se encontraron PDFs. Pon tus archivos en la carpeta 'data'.")
        return

    # =========================================================================
    # PASO 2: CHUNKING (Troceado)
    # =========================================================================
    # Dividimos el texto en fragmentos de 1000 caracteres con solapamiento
    # de 200 caracteres para no perder contexto entre páginas.
    # 
    # Ejemplo: Si un párrafo habla de "dosis de metotrexato" y está partido
    # entre dos chunks, el solapamiento asegura que ambos chunks tengan
    # el contexto completo.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # Tamaño máximo de cada fragmento
        chunk_overlap=200     # Solapamiento entre fragmentos consecutivos
    )
    chunks = text_splitter.split_documents(documentos)
    print(f"🧩 Documentos divididos en {len(chunks)} fragmentos de información.")

    # =========================================================================
    # PASO 3: GENERAR EMBEDDINGS Y GUARDAR
    # =========================================================================
    # Usamos un modelo de embeddings ligero (all-MiniLM-L6-v2) que:
    # - Corre en CPU (no necesita GPU)
    # - Es rápido (~100ms por fragmento)
    # - Produce vectores de 384 dimensiones
    # - Es multilingüe (funciona bien con español)
    print("🧠 Generando base de datos vectorial (esto puede tardar un poco)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Si ya existe una DB anterior, la borramos para re-crearla limpia
    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)

    # Crear la base de datos vectorial con ChromaDB
    # ChromaDB guarda los vectores en disco para persistencia
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    
    print(f"✅ ¡Éxito! Base de conocimientos guardada en '{DB_PATH}'.")
    print("   Ahora tu IA puede consultar 180 páginas en milisegundos.")


if __name__ == "__main__":
    ingest_data()
