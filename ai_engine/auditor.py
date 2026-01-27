"""
================================================================================
AUDITOR.PY - Agente Auditor de Seguridad Farmacéutica
================================================================================

Este módulo implementa un agente de IA que valida la seguridad de las
prescripciones médicas consultando una base de conocimientos (RAG).

FUNCIÓN PRINCIPAL:
- Recibir una pauta médica en formato JSON
- Buscar información relevante en las guías médicas indexadas
- Usar Llama3 para analizar si hay contraindicaciones o alertas
- Devolver un veredicto (aprobado/rechazado) con explicaciones

NOTA: Este módulo es una versión anterior del sistema de validación.
La versión actual más completa está en ai_backend/agents/tripulacion.py
================================================================================
"""

from langchain_community.llms import Ollama
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
import json


class AgenteAuditor:
    """
    Agente de IA que audita la seguridad de prescripciones médicas.
    
    Usa RAG (Retrieval Augmented Generation) para consultar guías médicas
    y determinar si una prescripción es segura.
    
    Atributos:
        llm: Modelo de lenguaje Ollama (Llama3) para razonamiento
        db: Base de datos vectorial ChromaDB con las guías indexadas
    """
    
    def __init__(self):
        """
        Inicializa el auditor con el modelo de IA y la base de conocimientos.
        
        - Llama3 con temperature=0 para respuestas deterministas
        - ChromaDB con embeddings de nomic-embed-text para búsqueda semántica
        """
        self.llm = Ollama(model="llama3", temperature=0)
        self.db = Chroma(
            persist_directory="ai_engine/vector_db",
            embedding_function=OllamaEmbeddings(model="nomic-embed-text")
        )

    def validar_pauta(self, pauta_json: dict) -> dict:
        """
        Valida una pauta médica contra las guías de seguridad.
        
        Args:
            pauta_json: Diccionario con la estructura:
                {
                    "lista_medicamentos": [
                        {"nombre": "Ibuprofeno", "dosis": "400mg", ...}
                    ]
                }
        
        Returns:
            dict: Resultado de la validación con estructura:
                {
                    "evidencia_encontrada": str,  # Cita del texto relevante
                    "aprobado": bool,             # True si es seguro
                    "alertas": list[str]          # Lista de alertas si las hay
                }
        
        PROCESO:
        1. Extrae los nombres de medicamentos de la pauta
        2. Busca información relevante en la DB vectorial (RAG)
        3. Construye un prompt específico para el LLM
        4. Parsea la respuesta JSON del LLM
        """
        # Convertir la pauta a texto para el prompt
        pauta_texto = json.dumps(pauta_json, indent=2)
        
        # Extraer nombres de medicamentos para la búsqueda
        medicamentos = [m['nombre'] for m in pauta_json.get('lista_medicamentos', [])]
        nombres_str = ", ".join(medicamentos)
        
        # =================================================================
        # PASO 1: BÚSQUEDA RAG
        # =================================================================
        # Query centrada en el medicamento específico para obtener
        # información de dosis, frecuencia, contraindicaciones y seguridad
        query = f"Dosis, frecuencia, contraindicaciones y seguridad de: {nombres_str}"
        
        # Buscar los 5 fragmentos más relevantes
        docs_relacionados = self.db.similarity_search(query, k=5)
        contexto_pdf = "\n\n".join([doc.page_content for doc in docs_relacionados])

        print(f"\n🔎 DEBUG: Analizando {nombres_str}...")

        # =================================================================
        # PASO 2: CONSTRUIR PROMPT PARA EL LLM
        # =================================================================
        # El prompt incluye reglas estrictas para evitar confusiones
        # cuando el contexto menciona otros medicamentos
        prompt = f"""
        Eres un Auditor Farmacéutico. Estás validando una receta de: {nombres_str}.
        
        CONTEXTO RECUPERADO DE LA BIBLIOTECA:
        "
        {contexto_pdf}
        "

        RECETA A ANALIZAR:
        {pauta_texto}

        REGLAS DE ORO (LÉELAS ATENTAMENTE):
        1. SOLO busca riesgos para el medicamento: {nombres_str}.
        2. Si el CONTEXTO habla de OTROS medicamentos (ej: Metotrexato) pero la receta es de {nombres_str}, IGNORA esa parte del contexto. ¡No te confundas!
        3. Si no encuentras contraindicaciones específicas para {nombres_str} en el contexto, APRUEBA la receta.
        
        Responde en JSON:
        {{
            "evidencia_encontrada": "Cita del texto sobre {nombres_str} (o 'No hay datos relevantes')...",
            "aprobado": true/false,
            "alertas": ["Solo si aplica a {nombres_str}..."]
        }}
        """

        # =================================================================
        # PASO 3: INVOCAR LLM Y PARSEAR RESPUESTA
        # =================================================================
        try:
            respuesta = self.llm.invoke(prompt)
            # Extraer el JSON de la respuesta (puede haber texto adicional)
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}') + 1
            return json.loads(respuesta[inicio:fin])
        except Exception as e:
            # En caso de error, rechazar por precaución
            return {"aprobado": False, "alertas": ["Error técnico"], "debug": str(e)}
