"""
================================================================================
RAG_ENGINE.PY - Motor de Búsqueda Semántica (RAG) para Pacientes
================================================================================

Este módulo implementa el sistema RAG (Retrieval Augmented Generation) que
permite al chatbot de pacientes consultar las guías médicas y fichas técnicas.

DIFERENCIAS CON ai_backend/:
- Este módulo usa FAISS (más rápido para consultas simples)
- Usa Ollama embeddings + ChatOllama para generar respuestas
- Diseñado para respuestas amigables para pacientes

PROCESO:
1. cargar_conocimiento(): Carga o crea el índice FAISS de los PDFs
2. consultar_rag(): Busca información y genera respuesta con Llama3

MODELOS USADOS:
- Embeddings: nomic-embed-text (Ollama)
- Chat: llama3 (Ollama)

REQUISITOS:
- Ollama corriendo en localhost:11434
- PDFs en la carpeta 'data/'
================================================================================
"""

import os
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Configuración de modelos
MODELO_CHAT = "llama3"
MODELO_EMBEDDINGS = "nomic-embed-text" 

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'data')           # Carpeta con PDFs
VECTOR_DB_PATH = os.path.join(BASE_DIR, 'faiss_index_ollama')  # Caché del índice


def cargar_conocimiento():
    """
    Carga el índice FAISS existente o crea uno nuevo desde los PDFs.
    
    PROCESO:
    1. Si existe el índice en disco, cargarlo (rápido)
    2. Si no existe, procesar los PDFs y crear el índice
    
    Returns:
        FAISS: Objeto vectorstore listo para búsquedas, o None si hay error
    """
    print(f"\n--- 🏁 GESTOR DE CONOCIMIENTO RAG ---")
    embeddings = OllamaEmbeddings(model=MODELO_EMBEDDINGS)

    # =========================================================================
    # PASO 1: INTENTAR CARGAR CACHÉ
    # =========================================================================
    if os.path.exists(VECTOR_DB_PATH):
        print(f"💾 Cargando índice existente...")
        try:
            # allow_dangerous_deserialization=True porque confiamos en nuestro propio índice
            vectorstore = FAISS.load_local(
                VECTOR_DB_PATH, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
            print("🚀 ¡Carga completada!")
            return vectorstore
        except Exception as e:
            print(f"⚠️ Error caché: {e}. Regenerando...")

    # =========================================================================
    # PASO 2: CREAR NUEVO ÍNDICE SI NO EXISTE
    # =========================================================================
    print(f"📂 Escaneando documentos en: {DATA_PATH}")
    if not os.path.exists(DATA_PATH): 
        return None
    
    try:
        # Cargar todos los PDFs del directorio
        loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        if not documents: 
            return None
        
        print(f"✅ Leídas {len(documents)} páginas.")
        
        # Trocear en fragmentos pequeños para mejor precisión
        # chunk_size=400 es más pequeño que en otros módulos porque
        # las preguntas de pacientes suelen ser más específicas
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400, 
            chunk_overlap=100
        )
        texts = text_splitter.split_documents(documents)
        
        print(f"🧠 Vectorizando {len(texts)} fragmentos con Ollama...")
        vectorstore = FAISS.from_documents(texts, embeddings)
        
        # Guardar en disco para la próxima vez
        vectorstore.save_local(VECTOR_DB_PATH)
        print(f"💾 Guardado en disco.")
        return vectorstore
        
    except Exception as e:
        print(f"🔥 ERROR RAG: {e}")
        return None


def consultar_rag(vectorstore, pregunta):
    """
    Consulta el RAG y genera una respuesta para el paciente.
    
    Args:
        vectorstore: Índice FAISS cargado
        pregunta: Pregunta del paciente en lenguaje natural
        
    Returns:
        str: Respuesta generada, o "NO_CONTEXT" si no hay información
    """
    if not vectorstore: 
        return "NO_CONTEXT"
    
    print(f"\n🔎 PREGUNTA USUARIO: {pregunta}")
    
    # =========================================================================
    # PASO 1: BÚSQUEDA DE DOCUMENTOS RELEVANTES
    # =========================================================================
    docs = vectorstore.similarity_search(pregunta, k=6)
    
    # Debug: mostrar fragmentos encontrados
    print(f"📚 EVIDENCIA ENCONTRADA ({len(docs)} fragmentos):")
    contexto_texto = ""
    for i, doc in enumerate(docs):
        preview = doc.page_content.replace('\n', ' ')[:100]
        print(f"   [{i+1}] {preview}...")
        contexto_texto += doc.page_content + "\n\n"

    # =========================================================================
    # PASO 2: GENERAR RESPUESTA CON LLM
    # =========================================================================
    # Prompt diseñado para respuestas amigables para pacientes
    template = """Eres un asistente médico útil y amable.
    Usa la siguiente información de contexto (extraída de guías médicas y fichas técnicas) para responder a la pregunta.
    
    CONTEXTO:
    {context}
    
    PREGUNTA: 
    {question}
    
    INSTRUCCIONES:
    1. Si encuentras la respuesta en el contexto, explícala de forma sencilla en español.
    2. Si el contexto menciona algo relacionado pero no es exacto, di "Según los documentos..." y explica lo que encuentres.
    3. Solo si NO hay absolutamente NADA relacionado, di "NO_CONTEXT".
    """
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    
    # Usar temperatura baja para respuestas más precisas
    llm = ChatOllama(model=MODELO_CHAT, temperature=0.1)
    
    # Crear cadena de QA
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # "stuff" = concatenar todos los documentos
        retriever=vectorstore.as_retriever(search_kwargs={"k": 6}),
        chain_type_kwargs={"prompt": prompt}
    )

    try:
        res = qa_chain.invoke(pregunta)
        respuesta = res.get("result", "").strip() if isinstance(res, dict) else str(res).strip()
        print(f"🤖 RESPUESTA GENERADA: {respuesta[:50]}...")
        return respuesta
    except Exception as e:
        print(f"❌ Error generando respuesta: {e}")
        return "NO_CONTEXT"
