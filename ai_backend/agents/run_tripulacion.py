"""
================================================================================
RUN_TRIPULACION.PY - Ejecutor CLI de Validación Médica
================================================================================

Este script es un punto de entrada alternativo para ejecutar la validación
médica desde línea de comandos. Recibe datos vía stdin en formato JSON y
devuelve el resultado por stdout.

FLUJO:
1. Lee JSON de stdin con: texto_medico, peso_paciente, id_paciente
2. Consulta el RAG para obtener evidencia de las guías médicas
3. Usa el LLM (Ollama/Llama3) para analizar y decidir
4. Devuelve JSON estructurado con el resultado

USO:
    echo '{"texto_medico": "...", "peso_paciente": 30}' | python run_tripulacion.py

NOTA: Este archivo es una alternativa más simple a tripulacion.py, sin usar
el framework completo de CrewAI Agents.
================================================================================
"""

import json
import os
import sys

from crewai import LLM
from ai_backend.tools.mis_herramientas import ProcesarRecetaTool, ConsultarGuiaRAGTool

# Desactivar telemetría de CrewAI para evitar problemas de conexión
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")


def _read_payload():
    """
    Lee y parsea el JSON de entrada desde stdin.
    
    Returns:
        dict: Datos de entrada o diccionario vacío si hay error
    """
    raw = sys.stdin.read()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _render_output(res):
    """
    Convierte la respuesta del LLM a string JSON.
    
    Maneja diferentes tipos de respuesta:
    - dict/list: serializa directamente
    - Objeto con json_dict: usa ese atributo
    - Objeto con raw: usa ese atributo
    - Otro: convierte a string
    
    Args:
        res: Respuesta del LLM en cualquier formato
        
    Returns:
        str: Respuesta serializada como JSON string
    """
    if isinstance(res, (dict, list)):
        return json.dumps(res, ensure_ascii=False)
    if hasattr(res, "json_dict") and res.json_dict:
        return json.dumps(res.json_dict, ensure_ascii=False)
    if hasattr(res, "raw"):
        return str(res.raw)
    return str(res)


def main():
    """
    Función principal que orquesta la validación médica.
    
    PASOS:
    1. Leer datos de entrada (texto médico, peso, id paciente)
    2. Inicializar LLM y herramientas RAG
    3. Consultar evidencia en las guías médicas
    4. Construir prompt para el LLM con la evidencia
    5. Obtener decisión del LLM (APROBADA/ALERTA/RECHAZADA)
    6. Estructurar y devolver resultado
    """
    # --- 1. LEER DATOS DE ENTRADA ---
    payload = _read_payload()
    texto_medico = payload.get("texto_medico", "")
    peso_paciente = payload.get("peso_paciente", 0)
    id_paciente = payload.get("id_paciente", "")

    # --- 2. INICIALIZAR LLM Y HERRAMIENTAS ---
    # Usamos Ollama con Llama3 corriendo localmente
    llm = LLM(model="ollama/llama3", base_url="http://localhost:11434")
    herramienta_rag = ConsultarGuiaRAGTool()
    herramienta_proceso = ProcesarRecetaTool()

    # --- 3. CONSULTAR RAG PARA OBTENER EVIDENCIA ---
    evidencia = herramienta_rag._run(
        f"¿Cuál es la dosis recomendada y si está indicado {texto_medico} para AIJ?"
    )

    # --- 4. CONSTRUIR PROMPT PARA EL LLM ---
    # El prompt incluye el schema JSON esperado, la orden médica,
    # el peso del paciente y la evidencia del RAG
    prompt = f"""
Eres un experto clínico. Con la evidencia y la orden médica, devuelve SOLO un JSON válido con estas claves:
{{
  "farmaco": str,
  "dosis_mg_kg": number|null,
  "frecuencia_texto": str,
  "frecuencia_horas": integer|null,
  "es_tratamiento_aij": boolean,
  "razon_decision": str,
  "decision": "APROBADA"|"ALERTA"|"RECHAZADA"
}}

Orden médica: "{texto_medico}"
Peso: {peso_paciente}kg

Evidencia RAG:
{evidencia}

Reglas:
- RECHAZADA si contraindicado/toxicidad o dosis fuera de guía.
- ALERTA si falta evidencia suficiente.
- APROBADA si indicado y dosis correcta.
"""

    # --- 5. OBTENER RESPUESTA DEL LLM ---
    respuesta = llm.call(prompt)

    # --- 6. PARSEAR RESPUESTA JSON ---
    # El LLM puede devolver texto adicional, extraemos solo el JSON
    raw = _render_output(respuesta)
    inicio = raw.find("{")
    fin = raw.rfind("}")
    data = {}
    if inicio != -1 and fin != -1 and fin > inicio:
        try:
            data = json.loads(raw[inicio:fin + 1])
        except Exception:
            data = {}

    # --- 7. VALIDAR CAMPOS REQUERIDOS ---
    required_keys = {
        "farmaco",
        "dosis_mg_kg",
        "frecuencia_texto",
        "frecuencia_horas",
        "es_tratamiento_aij",
        "razon_decision",
        "decision",
    }
    
    # Si el LLM no devolvió el JSON esperado, devolver error
    if not data or not required_keys.intersection(data.keys()):
        error_payload = {
            "estado": "Error",
            "analisis": {},
            "auditoria": {
                "es_aij": None,
                "razon": "El LLM no devolvió el JSON esperado.",
                "raw_output": raw,
            },
        }
        sys.stdout.write(json.dumps(error_payload, ensure_ascii=False))
        return

    # --- 8. EXTRAER DATOS DE LA RESPUESTA ---
    farmaco = data.get("farmaco") or "Desconocido"
    dosis_mg_kg = data.get("dosis_mg_kg")
    frecuencia_texto = data.get("frecuencia_texto") or ""
    frecuencia_horas = data.get("frecuencia_horas")
    es_tratamiento_aij = bool(data.get("es_tratamiento_aij")) if "es_tratamiento_aij" in data else False
    razon_decision = data.get("razon_decision") or "Sin motivo."
    decision = data.get("decision")

    # --- 9. PROCESAR Y ESTRUCTURAR RESULTADO ---
    result = herramienta_proceso._run(
        id_paciente=str(id_paciente),
        medico="",
        farmaco=farmaco,
        peso_paciente=float(peso_paciente),
        dosis_mg_kg=dosis_mg_kg,
        frecuencia_texto=frecuencia_texto,
        frecuencia_horas=frecuencia_horas,
        es_tratamiento_aij=es_tratamiento_aij,
        razon_decision=razon_decision,
        decision=decision
    )

    # --- 10. DEVOLVER RESULTADO POR STDOUT ---
    sys.stdout.write(_render_output(result))


if __name__ == "__main__":
    main()
