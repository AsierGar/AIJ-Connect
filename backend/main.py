"""
================================================================================
MAIN.PY - API REST del Backend (FastAPI)
================================================================================

Este módulo expone la API REST que conecta la aplicación móvil/web
con los agentes de IA para procesar prescripciones médicas.

ENDPOINTS:
    POST /procesar-seguro
        Recibe texto de voz/prescripción y devuelve:
        - Pauta estructurada (medicamentos, dosis, frecuencia)
        - Análisis de seguridad (aprobado/alertas)

ARQUITECTURA:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  App Móvil      │────▶│  FastAPI        │────▶│  Agentes IA     │
│  (Streamlit)    │     │  /procesar      │     │  (Ollama)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘

USO:
    uvicorn backend.main:app --reload --port 8000
    
    # Probar endpoint:
    curl -X POST http://localhost:8000/procesar-seguro \
         -H "Content-Type: application/json" \
         -d '{"texto_voz": "Ibuprofeno 10mg/kg cada 8h", "peso_paciente": 30}'

NOTA: Este backend usa los agentes de ai_engine/ (versión con Ollama).
La aplicación principal ahora usa ai_backend/ que tiene mejor integración.
================================================================================
"""

from fastapi import FastAPI
from pydantic import BaseModel
from ai_engine.structurer import AgenteEstructurador
from ai_engine.auditor import AgenteAuditor

# Crear instancia de FastAPI
app = FastAPI()

# Inicializar los agentes de IA (se cargan una vez al iniciar el servidor)
estructurador = AgenteEstructurador()
auditor = AgenteAuditor()


class RecetaInput(BaseModel):
    """
    Esquema de datos de entrada para el endpoint de procesamiento.
    
    Atributos:
        texto_voz: Texto de la prescripción (puede venir de reconocimiento de voz)
        peso_paciente: Peso del paciente en kg (para calcular dosis)
    """
    texto_voz: str
    peso_paciente: float = 0.0


@app.post("/procesar-seguro")
def procesar_receta(datos: RecetaInput):
    """
    Procesa una prescripción médica y valida su seguridad.
    
    Args:
        datos: RecetaInput con texto_voz y peso_paciente
        
    Returns:
        dict: Resultado con dos secciones:
            {
                "pauta_generada": {
                    "tratamiento_secuencial": [
                        {
                            "nombre": "Ibuprofeno",
                            "dosis": "10mg/kg",
                            "dosis_calculada": "300 mg",
                            ...
                        }
                    ]
                },
                "analisis_seguridad": {
                    "aprobado": true,
                    "alertas": [],
                    "evidencia_encontrada": "..."
                }
            }
    
    PROCESO:
    1. El AgenteEstructurador extrae la información del texto
    2. El AgenteMatematico (interno) calcula las dosis exactas
    3. El AgenteAuditor valida contra las guías médicas
    """
    # Debug: mostrar qué datos recibimos
    print(f"\n📨 BACKEND RECIBIÓ:")
    print(f"   - Texto: '{datos.texto_voz}'")
    print(f"   - Peso: {datos.peso_paciente} kg")

    # PASO 1: Estructurar el texto y calcular dosis
    pauta_json = estructurador.estructurar_texto(datos.texto_voz, datos.peso_paciente)
    
    # PASO 2: Auditar la seguridad contra las guías médicas
    analisis_seguridad = auditor.validar_pauta(pauta_json)
    
    # Devolver resultado combinado
    return {
        "pauta_generada": pauta_json,
        "analisis_seguridad": analisis_seguridad
    }
