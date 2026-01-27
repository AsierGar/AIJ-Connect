"""
================================================================================
MIS_HERRAMIENTAS.PY - Herramientas de IA para Validación Médica
================================================================================

Este módulo define las herramientas o tools que usa el sistema de IA para:
1. Consultar las guías médicas indexadas (RAG)
2. Procesar y estructurar las prescripciones médicas

Las herramientas siguen el patrón de CrewAI BaseTool, lo que permite
usarlas tanto de forma independiente como con agentes de CrewAI.

HERRAMIENTAS:
- ConsultarGuiaRAGTool: Busca información en las guías médicas
- ProcesarRecetaTool: Estructura y valida la prescripción

ARQUITECTURA RAG (Retrieval Augmented Generation):
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Pregunta  │────▶│  Embedding  │────▶│  ChromaDB   │
│   "dosis    │     │  (vector)   │     │  (búsqueda) │
│   metotr.." │     └─────────────┘     └─────────────┘
└─────────────┘                                │
                                               ▼
                                    ┌─────────────────────┐
                                    │  Top 5 fragmentos   │
                                    │  más relevantes     │
                                    └─────────────────────┘
================================================================================
"""

import json
import os
from datetime import datetime
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Imports para RAG (Retrieval Augmented Generation)
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Ruta a la base de datos vectorial
DB_PATH = "ai_backend/vector_db"


# =============================================================================
# ESQUEMAS DE DATOS (Pydantic Models)
# =============================================================================

class DatosReceta(BaseModel):
    """
    Esquema de datos para procesar una prescripción médica.
    
    Todos los campos son validados por Pydantic antes de procesar.
    """
    id_paciente: str = Field(..., description="El ID del paciente.")
    medico: str = Field("", description="Nombre del médico que prescribe.")
    farmaco: str = Field(..., description="Nombre genérico del medicamento.")
    peso_paciente: float = Field(..., description="Peso del paciente en Kg.")
    dosis_mg_kg: Optional[float] = Field(None, description="Dosis en mg por cada kg de peso.")
    frecuencia_texto: str = Field("", description="Texto de frecuencia (ej: 'cada 8 horas').")
    frecuencia_horas: Optional[int] = Field(None, description="Número de horas entre tomas.")
    es_tratamiento_aij: bool = Field(..., description="True si cumple protocolo AIJ.")
    razon_decision: str = Field(..., description="Explicación técnica basada en la guía.")
    decision: Optional[str] = Field(None, description="Severidad: APROBADA/ALERTA/RECHAZADA.")


class ConsultaRAGInput(BaseModel):
    """Esquema para consultas al RAG."""
    pregunta: str = Field(..., description="La duda clínica o fármaco a consultar.")


# =============================================================================
# HERRAMIENTA 1: CONSULTAR GUÍAS MÉDICAS (RAG)
# =============================================================================

class ConsultarGuiaRAGTool(BaseTool):
    """
    Herramienta para buscar información en las guías médicas indexadas.
    
    Usa búsqueda semántica (por significado) sobre los PDFs indexados
    en ChromaDB. Esto permite encontrar información relevante aunque
    las palabras exactas no coincidan.
    
    EJEMPLO:
        >>> rag = ConsultarGuiaRAGTool()
        >>> resultado = rag._run("dosis metotrexato niños")
        >>> print(resultado)
        "--- EVIDENCIA ENCONTRADA ---
         [Fuente: ficha tecnica metotrexate.pdf - Pág 5]:
         En pacientes pediátricos con AIJ, se recomiendan dosis bajas
         (menos de 25 mg/semana)..."
    """
    name: str = "Consultar Guia Medica RAG"
    description: str = "Busca información en las guías médicas PDF indexadas."
    args_schema: Type[BaseModel] = ConsultaRAGInput

    def _run(self, pregunta: str) -> str:
        """
        Ejecuta la búsqueda semántica en las guías médicas.
        
        Args:
            pregunta: Texto de la consulta (ej: "dosis metotrexato niños")
            
        Returns:
            str: Fragmentos relevantes encontrados o mensaje de error
        """
        try:
            # Verificar que existe la DB vectorial
            if not os.path.exists(DB_PATH):
                return "Error: No existe DB vectorial. Ejecuta ingest_knowledge.py primero."
            
            # Cargar embeddings y DB
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            
            # -----------------------------------------------------------------
            # MAPEO DE FÁRMACOS A SUS FICHAS TÉCNICAS
            # -----------------------------------------------------------------
            # Esto permite búsquedas más precisas cuando sabemos qué fármaco
            # está buscando el usuario
            farmacos_fichas = {
                "metotrexato": "data/ficha tecnica metotrexate.pdf",
                "metotrexate": "data/ficha tecnica metotrexate.pdf",
                "methotrexate": "data/ficha tecnica metotrexate.pdf",
                "mtx": "data/ficha tecnica metotrexate.pdf",
                "ibuprofeno": "data/ficha tecnica ibuprofeno.pdf",
                "ibuprofen": "data/ficha tecnica ibuprofeno.pdf",
                "paracetamol": "data/ficha tecnica paracetamol.pdf",
                "acetaminofen": "data/ficha tecnica paracetamol.pdf",
                "prednisona": "data/ficha tecnica prednisona.pdf",
                "tocilizumab": "data/ficha tecnica Tocilizumab.pdf",
                "adalimumab": "data/ficha tecnica Adalimumab.pdf",
                "humira": "data/ficha tecnica Adalimumab.pdf",
            }
            
            # Identificar qué fármaco se está buscando
            pregunta_lower = pregunta.lower()
            ficha_objetivo = None
            farmaco_encontrado = None
            
            for farmaco, ficha in farmacos_fichas.items():
                if farmaco in pregunta_lower:
                    ficha_objetivo = ficha
                    farmaco_encontrado = farmaco
                    break
            
            resultados_final = []
            
            # -----------------------------------------------------------------
            # ESTRATEGIA 1: Búsqueda específica en la ficha del fármaco
            # -----------------------------------------------------------------
            if ficha_objetivo:
                try:
                    # Filtrar por metadata.source para buscar solo en esa ficha
                    resultados_ficha = vector_db.similarity_search(
                        f"dosis máxima {farmaco_encontrado} mg kg niños",
                        k=6,  # Top 6 resultados
                        filter={"source": ficha_objetivo}
                    )
                    if resultados_ficha:
                        resultados_final = resultados_ficha
                        print(f"📄 Encontrados {len(resultados_final)} resultados en {ficha_objetivo}")
                except Exception as e:
                    print(f"⚠️ Error en búsqueda filtrada: {e}")
            
            # -----------------------------------------------------------------
            # ESTRATEGIA 2: Búsqueda general (fallback)
            # -----------------------------------------------------------------
            if not resultados_final:
                resultados_final = vector_db.similarity_search(pregunta, k=5)
                print(f"🔍 Usando {len(resultados_final)} resultados de búsqueda general")
            
            if not resultados_final:
                return "No se encontró información en las guías médicas."
            
            # -----------------------------------------------------------------
            # FORMATEAR RESULTADOS
            # -----------------------------------------------------------------
            contexto = "--- EVIDENCIA ENCONTRADA ---\n"
            for doc in resultados_final:
                fuente = os.path.basename(doc.metadata.get('source', 'Documento'))
                pagina = doc.metadata.get('page', '?')
                contexto += f"\n[Fuente: {fuente} - Pág {pagina}]:\n{doc.page_content}\n"
            
            return contexto
            
        except Exception as e: 
            return f"Error RAG: {e}"


# =============================================================================
# HERRAMIENTA 2: PROCESAR PRESCRIPCIÓN MÉDICA
# =============================================================================

class ProcesarRecetaTool(BaseTool):
    """
    Herramienta para estructurar y validar prescripciones médicas.
    
    Recibe los datos extraídos de la prescripción y genera un JSON
    estructurado con el análisis y la decisión.
    
    NOTA: Esta herramienta NO guarda nada en disco, solo analiza y
    devuelve el resultado. El guardado se hace en la capa de UI.
    
    EJEMPLO:
        >>> proc = ProcesarRecetaTool()
        >>> resultado = proc._run(
        ...     id_paciente="P_001",
        ...     farmaco="Metotrexato",
        ...     peso_paciente=25,
        ...     dosis_mg_kg=0.5,
        ...     ...
        ... )
        >>> print(resultado)
        '{"estado": "Aprobada", "analisis": {...}, "auditoria": {...}}'
    """
    name: str = "Procesar Prescripcion Medica"
    description: str = "Calcula dosis y estructura la receta para revisión médica. NO guarda nada, solo analiza."
    args_schema: Type[BaseModel] = DatosReceta

    def _run(
        self,
        id_paciente: str,
        medico: str,
        farmaco: str,
        peso_paciente: float,
        dosis_mg_kg: Optional[float],
        frecuencia_texto: str,
        frecuencia_horas: Optional[int],
        es_tratamiento_aij: bool,
        razon_decision: str,
        decision: Optional[str] = None
    ) -> str:
        """
        Procesa la prescripción y genera el JSON de resultado.
        
        Args:
            id_paciente: ID único del paciente
            medico: Nombre del médico prescriptor
            farmaco: Nombre del medicamento
            peso_paciente: Peso en kg
            dosis_mg_kg: Dosis por kg de peso (puede ser None)
            frecuencia_texto: Descripción de la frecuencia
            frecuencia_horas: Intervalo en horas entre dosis
            es_tratamiento_aij: Si cumple protocolos AIJ
            razon_decision: Explicación de la decisión
            decision: APROBADA, ALERTA o RECHAZADA
            
        Returns:
            str: JSON con el análisis estructurado
        """
        # Calcular dosis total si tenemos dosis por kg
        if dosis_mg_kg is None:
            dosis_str = "N/D"
        else:
            dosis_total = peso_paciente * dosis_mg_kg
            dosis_str = f"{dosis_total:.0f} mg"

        # Construir y devolver JSON estructurado
        return json.dumps({
            "estado": "Aprobada" if es_tratamiento_aij else "Alerta",
            "decision": decision,
            "analisis": {
                "farmaco": farmaco,
                "dosis_calculada": dosis_str,
                "dosis_mg_kg_detectada": dosis_mg_kg,
                "frecuencia": frecuencia_texto,
                "frecuencia_horas": frecuencia_horas
            },
            "auditoria": {
                "es_aij": es_tratamiento_aij,
                "razon": razon_decision
            }
        })
