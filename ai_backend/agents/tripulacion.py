"""
================================================================================
TRIPULACION.PY - Sistema de Validación Médica con IA (RAG + Reglas)
================================================================================

Este módulo implementa la validación inteligente de prescripciones médicas
para pacientes con Artritis Idiopática Juvenil (AIJ).

CARACTERÍSTICAS:
- Extrae fármaco, dosis y frecuencia del texto médico usando regex
- Consulta guías médicas indexadas (RAG) para obtener evidencia
- Compara la dosis prescrita con los límites de las guías
- Decide: APROBADA, ALERTA o RECHAZADA

ARQUITECTURA:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Texto Médico   │────▶│  Extracción     │────▶│  Consulta RAG   │
│  (input)        │     │  (regex)        │     │  (ChromaDB)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌─────────────────┐             ▼
                        │  JSON Resultado │◀────────────────────────
                        │  (output)       │     Lógica de Decisión
                        └─────────────────┘

DECISIONES:
- APROBADA: Fármaco indicado y dosis dentro del rango seguro
- ALERTA: Fármaco indicado pero no se pudo verificar dosis
- RECHAZADA: Dosis excesiva o contraindicación encontrada
================================================================================
"""

import os
import sys
import json
import re

# Añadir path para imports relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Desactivar telemetría para evitar problemas en Streamlit
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

from ai_backend.tools.mis_herramientas import ProcesarRecetaTool, ConsultarGuiaRAGTool


def ejecutar_validacion_medica(texto_medico, peso_paciente, id_paciente, timeout_seconds=60):
    """
    Valida un plan terapéutico consultando las guías médicas (RAG) y comparando
    la dosis prescrita con la dosis máxima permitida según las guías.
    
    Args:
        texto_medico (str): Texto libre con la prescripción médica
                           Ej: "Metotrexato 15mg semanal"
        peso_paciente (float): Peso del paciente en kg
        id_paciente (str): Identificador único del paciente
        timeout_seconds (int): Timeout para la operación (no usado actualmente)
    
    Returns:
        dict: Resultado estructurado con el schema:
            {
                "estado": "Aprobada|Alerta|Rechazada",
                "decision": "APROBADA|ALERTA|RECHAZADA",
                "analisis": {
                    "farmaco": str,
                    "dosis_calculada": str,
                    "dosis_mg_kg_detectada": float|None,
                    "frecuencia": str,
                    "frecuencia_horas": int|None
                },
                "auditoria": {
                    "es_aij": bool,
                    "razon": str,
                    "dosis_max_guia": float|None,
                    "evidencia_raw": str|None
                }
            }
    
    EJEMPLO:
        >>> resultado = ejecutar_validacion_medica(
        ...     "Metotrexato 30mg semanal",
        ...     peso_paciente=25,
        ...     id_paciente="P_001"
        ... )
        >>> print(resultado["decision"])
        "RECHAZADA"  # Porque 30mg >= 25mg (límite para dosis bajas)
    """
    print("🔄 EJECUTANDO VERSIÓN 2.0 DE VALIDACIÓN MÉDICA")
    
    # Inicializar herramientas
    rag = ConsultarGuiaRAGTool()
    proc = ProcesarRecetaTool()
    
    texto = texto_medico or ""
    texto_lower = texto.lower()
    
    # =========================================================================
    # PASO 1: EXTRAER FÁRMACO DEL TEXTO
    # =========================================================================
    # Lista de fármacos conocidos para AIJ (permite detección más precisa)
    farmacos_conocidos = [
        "ibuprofeno", "metotrexato", "metotrexate", "naproxeno", "paracetamol", 
        "prednisona", "adalimumab", "etanercept", "tocilizumab", "sulfasalazina", 
        "leflunomida", "hidroxicloroquina", "azatioprina", "ciclosporina", "infliximab"
    ]
    
    farmaco = None
    for f in farmacos_conocidos:
        if f in texto_lower:
            # Normalizar variantes (metotrexate -> metotrexato)
            if f == "metotrexate":
                farmaco = "Metotrexato"
            else:
                farmaco = f.capitalize()
            break
    
    # Si no se encontró en la lista, intentar extraer la primera palabra larga
    if not farmaco:
        match = re.search(r"\b([A-Za-zÁÉÍÓÚáéíóúñÑ]{4,})\b", texto)
        if match:
            farmaco = match.group(1).capitalize()
        else:
            farmaco = "Desconocido"
    
    # =========================================================================
    # PASO 2: EXTRAER DOSIS DEL TEXTO
    # =========================================================================
    # Buscar dosis en formato mg/kg (ej: "0.5 mg/kg")
    dosis_mg_kg = None
    dosis_match = re.search(r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*kg", texto, re.IGNORECASE)
    if dosis_match:
        dosis_mg_kg = float(dosis_match.group(1).replace(",", "."))
    
    # Buscar dosis absoluta en mg (ej: "30 mg semanal")
    dosis_absoluta = None
    dosis_abs_match = re.search(r"(\d+(?:[.,]\d+)?)\s*mg(?!\s*/\s*kg)", texto, re.IGNORECASE)
    if dosis_abs_match:
        dosis_absoluta = float(dosis_abs_match.group(1).replace(",", "."))
    
    # =========================================================================
    # PASO 3: EXTRAER FRECUENCIA
    # =========================================================================
    frecuencia_horas = None
    frecuencia_texto = ""
    
    # Buscar "cada X horas"
    freq_match = re.search(r"cada\s+(\d+)\s*h", texto, re.IGNORECASE)
    if freq_match:
        frecuencia_horas = int(freq_match.group(1))
        frecuencia_texto = f"cada {frecuencia_horas} horas"
    elif "semanal" in texto_lower:
        frecuencia_texto = "semanal"
        frecuencia_horas = 168  # 7 días * 24 horas
    elif "diario" in texto_lower or "diaria" in texto_lower:
        frecuencia_texto = "diario"
        frecuencia_horas = 24
    
    # =========================================================================
    # PASO 4: CONSULTAR RAG PARA OBTENER EVIDENCIA
    # =========================================================================
    evidencia_texto = ""
    
    # Variantes de nombres para mejorar la búsqueda en el RAG
    variantes_farmaco = {
        "Metotrexato": ["metotrexato", "metotrexate", "methotrexate", "MTX"],
        "Ibuprofeno": ["ibuprofeno", "ibuprofen"],
        "Paracetamol": ["paracetamol", "acetaminofen", "acetaminofén"],
        "Prednisona": ["prednisona", "prednisone"],
        "Tocilizumab": ["tocilizumab"],
        "Adalimumab": ["adalimumab", "humira"],
    }
    
    nombres_buscar = variantes_farmaco.get(farmaco, [farmaco.lower()])
    
    try:
        # Intentar búsqueda con diferentes variantes del nombre
        mejor_evidencia = ""
        for nombre in nombres_buscar:
            pregunta_rag = f"dosis {nombre} niños artritis juvenil mg"
            evidencia = rag._run(pregunta_rag)
            evidencia_str = str(evidencia or "")
            
            # Si encontramos el nombre del fármaco en la evidencia, es relevante
            if nombre.lower() in evidencia_str.lower() or farmaco.lower() in evidencia_str.lower():
                mejor_evidencia = evidencia_str
                print(f"📚 RAG Evidencia para {farmaco} (query: '{nombre}'):\n{evidencia_str[:500]}")
                break
            elif not mejor_evidencia:
                mejor_evidencia = evidencia_str
        
        evidencia_texto = mejor_evidencia
        if not any(n.lower() in evidencia_texto.lower() for n in nombres_buscar + [farmaco.lower()]):
            print(f"⚠️ RAG no encontró evidencia específica de {farmaco}. Evidencia recibida:\n{evidencia_texto[:300]}")
    except Exception as e:
        evidencia_texto = f"Error consultando RAG: {e}"
    
    evidencia_lower = evidencia_texto.lower()
    
    # =========================================================================
    # PASO 5: EXTRAER DOSIS MÁXIMA DE LA EVIDENCIA
    # =========================================================================
    dosis_max_guia = None
    dosis_max_texto = ""
    es_dosis_semanal = "semanal" in frecuencia_texto.lower() if frecuencia_texto else False
    
    # Patrones regex para detectar dosis máxima en las guías
    # Ordenados por especificidad (los más específicos primero)
    patrones_dosis_max = [
        # Patrones específicos de límite semanal
        (r"menos\s+de\s+(\d+(?:[.,]\d+)?)\s*mg\s*/?\s*semana", "semanal"),
        (r"dosis\s+bajas\s*\(?menos\s+de\s+(\d+(?:[.,]\d+)?)\s*mg", "semanal"),
        (r"dosis\s*m[áa]xima\s*(?:semanal\s*)?(?:de\s*)?(\d+(?:[.,]\d+)?)\s*mg", "semanal"),
        (r"m[áa]ximo\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*mg\s*/?\s*semana", "semanal"),
        # Patrones diarios
        (r"dosis\s*m[áa]xima\s*(?:diaria\s*)?(?:de\s*)?(\d+(?:[.,]\d+)?)\s*mg", "diario"),
        (r"no\s*(?:debe\s*)?exceder\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*mg", "diario"),
        (r"hasta\s*(\d+(?:[.,]\d+)?)\s*mg(?:\s*/\s*d[íi]a)?", "diario"),
        # Patrones por peso
        (r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*kg\s*/\s*d[íi]a", "mg_kg"),
        (r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*mg\s*/\s*semana", "semanal"),
    ]
    
    for patron, tipo in patrones_dosis_max:
        match = re.search(patron, evidencia_lower)
        if match:
            grupos = [g for g in match.groups() if g]
            if grupos:
                # Tomar el último valor (para rangos X-Y, tomar Y como máximo)
                valor = float(grupos[-1].replace(",", "."))
                dosis_max_guia = valor
                dosis_max_texto = f"{valor} mg/{tipo if tipo != 'diario' else 'día'}"
                print(f"📊 Dosis máxima encontrada: {dosis_max_texto} (patrón: {patron})")
                break
    
    # =========================================================================
    # PASO 6: LÓGICA DE DECISIÓN
    # =========================================================================
    es_aij = True
    decision = "APROBADA"
    razon = ""
    
    # --- Verificar contraindicaciones para AIJ ---
    contraindicacion_aij = False
    contexto_contra = ""
    
    patrones_contraindicacion = [
        r"contraindicado\s+(?:en|para)\s+(?:artritis|aij|niños|juvenil)",
        r"no\s+(?:indicado|recomendado)\s+(?:en|para)\s+(?:artritis|aij|niños)",
        r"no\s+usar\s+en\s+(?:artritis|aij|niños)",
    ]
    
    for patron in patrones_contraindicacion:
        match = re.search(patron, evidencia_lower)
        if match:
            contraindicacion_aij = True
            idx = match.start()
            contexto_contra = evidencia_texto[max(0, idx-30):min(len(evidencia_texto), idx+100)]
            break
    
    # --- Aplicar reglas de decisión ---
    if contraindicacion_aij:
        # CASO 1: Contraindicación explícita encontrada
        es_aij = False
        decision = "RECHAZADA"
        razon = f"⚠️ {farmaco} contraindicado para AIJ según la guía. Evidencia: '...{contexto_contra}...'"
    
    elif dosis_max_guia:
        # CASO 2: Tenemos dosis máxima de la guía, comparar
        # Calcular dosis total prescrita
        if dosis_mg_kg and peso_paciente:
            dosis_prescrita = dosis_mg_kg * float(peso_paciente)
        elif dosis_absoluta:
            dosis_prescrita = dosis_absoluta
        else:
            dosis_prescrita = None
        
        if dosis_prescrita:
            if dosis_prescrita >= dosis_max_guia:
                # Dosis excede el límite
                es_aij = False
                decision = "RECHAZADA"
                razon = f"⚠️ DOSIS EXCESIVA: Se prescribe {dosis_prescrita:.0f} mg pero la guía indica límite de {dosis_max_guia:.0f} mg ({dosis_max_texto}). Dosis ≥{dosis_max_guia:.0f} mg se consideran ALTAS."
            else:
                # Dosis dentro del rango
                es_aij = True
                decision = "APROBADA"
                razon = f"✅ Dosis {dosis_prescrita:.0f} mg dentro del rango seguro (límite: {dosis_max_guia:.0f} mg según guía)."
        else:
            # No pudimos calcular la dosis prescrita
            es_aij = True
            decision = "ALERTA"
            razon = f"ℹ️ {farmaco} indicado. Límite según guía: {dosis_max_guia:.0f} mg. No se pudo verificar la dosis prescrita."
    
    elif "no se encontr" in evidencia_lower or "error" in evidencia_lower or not evidencia_texto.strip():
        # CASO 3: No hay evidencia en el RAG
        es_aij = False
        decision = "ALERTA"
        razon = f"⚠️ No se encontró información de {farmaco} en las guías médicas. Verificar manualmente."
    
    else:
        # CASO 4: Hay evidencia pero no pudimos extraer dosis máxima
        if farmaco.lower() in evidencia_lower or "artritis" in evidencia_lower:
            es_aij = True
            decision = "ALERTA"
            extracto = evidencia_texto[:300].replace("\n", " ").strip()
            razon = f"ℹ️ {farmaco} encontrado en guías pero no se pudo extraer dosis máxima. Evidencia: '{extracto}...'"
        else:
            es_aij = False
            decision = "ALERTA"
            razon = f"⚠️ No se encontró evidencia clara de {farmaco} para AIJ en las guías."
    
    # =========================================================================
    # PASO 7: CALCULAR DOSIS PARA MOSTRAR
    # =========================================================================
    dosis_calculada = None
    if dosis_mg_kg and peso_paciente:
        dosis_calculada = dosis_mg_kg * float(peso_paciente)
    elif dosis_absoluta:
        dosis_calculada = dosis_absoluta
    
    # =========================================================================
    # PASO 8: GENERAR Y DEVOLVER RESULTADO
    # =========================================================================
    try:
        resultado = proc._run(
            id_paciente=str(id_paciente),
            medico="Sistema IA",
            farmaco=farmaco,
            peso_paciente=float(peso_paciente),
            dosis_mg_kg=dosis_mg_kg,
            frecuencia_texto=frecuencia_texto,
            frecuencia_horas=frecuencia_horas,
            es_tratamiento_aij=es_aij,
            razon_decision=razon,
            decision=decision
        )
        
        if isinstance(resultado, str):
            try:
                parsed = json.loads(resultado)
                # Añadir la dosis absoluta si la teníamos
                if dosis_absoluta and not dosis_mg_kg:
                    parsed["analisis"]["dosis_absoluta_mg"] = dosis_absoluta
                return parsed
            except json.JSONDecodeError:
                pass
        
        return resultado
        
    except Exception as e:
        # Fallback: devolver resultado estructurado manualmente
        return {
            "estado": "Aprobada" if decision == "APROBADA" else decision,
            "decision": decision,
            "analisis": {
                "farmaco": farmaco,
                "dosis_calculada": f"{dosis_calculada:.0f} mg" if dosis_calculada else "N/D",
                "dosis_mg_kg_detectada": dosis_mg_kg,
                "dosis_absoluta_mg": dosis_absoluta,
                "frecuencia": frecuencia_texto,
                "frecuencia_horas": frecuencia_horas
            },
            "auditoria": {
                "es_aij": es_aij,
                "razon": razon,
                "dosis_max_guia": dosis_max_guia,
                "evidencia_raw": evidencia_texto[:500] if evidencia_texto else None
            }
        }
