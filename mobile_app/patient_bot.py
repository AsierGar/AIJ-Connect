"""
================================================================================
PATIENT_BOT.PY - Chatbot Asistente para Pacientes
================================================================================

Este módulo implementa un chatbot inteligente que responde a las dudas
de los pacientes sobre su tratamiento y medicación.

CARACTERÍSTICAS:
- Guardrails de seguridad para derivar urgencias al médico
- Respuestas específicas para dosis olvidadas de cada medicamento
- Integración con RAG para consultar guías médicas
- Extracción de medicación actual del historial del paciente

PRIORIDADES DE RESPUESTA:
1. Guardrails: Detectar emergencias y derivar
2. Dosis olvidadas: Respuestas específicas por medicamento
3. Medicación actual: Extraer del plan de tratamiento
4. Citas: Información sobre gestión de citas
5. RAG: Consultar guías médicas para preguntas generales
6. Fallback: Derivar al médico si no hay respuesta

MEDICAMENTOS SOPORTADOS:
- Metotrexato (MTX)
- Ácido Fólico
- Ibuprofeno / Naproxeno
- Prednisona
- Biológicos: Adalimumab, Tocilizumab, Etanercept
================================================================================
"""

import streamlit as st
import os
import re

# Intentar importar el motor RAG (puede no estar disponible)
try:
    from rag_engine import cargar_conocimiento, consultar_rag
    RAG_DISPONIBLE = True
    print("✅ RAG Engine importado correctamente.")
except ImportError as e:
    print(f"❌ ERROR CRÍTICO IMPORTANDO RAG: {e}")
    RAG_DISPONIBLE = False
except Exception as e:
    print(f"❌ ERROR DESCONOCIDO EN RAG: {e}")
    RAG_DISPONIBLE = False

# Caché del vectorstore en sesión (para no recargarlo cada vez)
if "vectorstore_cache" not in st.session_state:
    st.session_state.vectorstore_cache = None


def _extraer_medicaciones_del_plan(plan_texto):
    """
    Extrae las medicaciones del plan de tratamiento y las formatea.
    
    Busca patrones de medicamentos conocidos en el texto del plan
    y extrae información de dosis y frecuencia cuando está disponible.
    
    Args:
        plan_texto: Texto del plan de tratamiento
        
    Returns:
        list: Lista de strings formateados con cada medicación
              Ej: ["💉 **Metotrexato** 15 mg (semanal)", "💊 **Ácido Fólico** 5 mg (diario)"]
              None si no se encontraron medicaciones
    """
    if not plan_texto:
        return None
    
    texto_lower = plan_texto.lower()
    medicaciones = []
    
    # Diccionario de medicamentos con sus variantes y emojis
    medicamentos_info = {
        "Metotrexato": {
            "variantes": ["metotrexato", "metotrexate", "mtx"],
            "emoji": "💉"
        },
        "Ácido Fólico": {
            "variantes": ["ácido fólico", "acido folico", "ac fólico", "ac folico", "acfol"],
            "emoji": "💊"
        },
        "Ibuprofeno": {
            "variantes": ["ibuprofeno", "ibuprofen"],
            "emoji": "💊"
        },
        "Naproxeno": {
            "variantes": ["naproxeno"],
            "emoji": "💊"
        },
        "Prednisona": {
            "variantes": ["prednisona", "prednisone", "corticoide"],
            "emoji": "💊"
        },
        "Adalimumab (Humira)": {
            "variantes": ["adalimumab", "humira"],
            "emoji": "💉"
        },
        "Tocilizumab": {
            "variantes": ["tocilizumab", "actemra"],
            "emoji": "💉"
        },
        "Etanercept": {
            "variantes": ["etanercept", "enbrel"],
            "emoji": "💉"
        }
    }
    
    for med_nombre, med_info in medicamentos_info.items():
        for variante in med_info["variantes"]:
            if variante in texto_lower:
                # Intentar extraer la dosis con regex
                patron_dosis = rf"{variante}[^\d]*(\d+(?:[.,]\d+)?)\s*mg"
                match = re.search(patron_dosis, texto_lower)
                dosis = match.group(1) + " mg" if match else ""
                
                # Detectar frecuencia en el contexto cercano
                frecuencia = ""
                idx = texto_lower.find(variante)
                contexto = texto_lower[idx:idx+100] if idx >= 0 else ""
                
                if "semanal" in contexto:
                    frecuencia = "semanal"
                elif "diario" in contexto or "cada día" in contexto or "/día" in contexto:
                    frecuencia = "diario"
                elif "quincenal" in contexto or "cada 2 semanas" in contexto:
                    frecuencia = "cada 2 semanas"
                elif "cada 8 horas" in contexto:
                    frecuencia = "cada 8 horas"
                elif "cada 12 horas" in contexto:
                    frecuencia = "cada 12 horas"
                elif any(dia in contexto for dia in ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]):
                    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
                    for dia in dias:
                        if dia in contexto:
                            frecuencia = f"los {dia}s"
                            break
                
                # Formatear la medicación
                med_str = f"{med_info['emoji']} **{med_nombre}**"
                if dosis:
                    med_str += f" {dosis}"
                if frecuencia:
                    med_str += f" ({frecuencia})"
                
                if med_str not in medicaciones:
                    medicaciones.append(med_str)
                break  # No buscar más variantes si ya encontramos una
    
    return medicaciones if medicaciones else None


def responder_duda_paciente(pregunta, historial_paciente, nombre_paciente):
    """
    Genera una respuesta a la pregunta del paciente.
    
    Args:
        pregunta: Texto de la pregunta del paciente
        historial_paciente: Lista de registros de visitas del paciente
        nombre_paciente: Nombre del paciente para personalizar respuestas
        
    Returns:
        str: Respuesta formateada en Markdown
    """
    p = pregunta.lower()
    
    # =========================================================================
    # 1. GUARDRAILS - Detectar situaciones de riesgo
    # =========================================================================
    
    # Saludos: responder amablemente
    if p in ["hola", "buenas", "gracias", "qué tal", "buenos días", "buenas tardes"]:
        return f"¡Hola {nombre_paciente}! Soy tu asistente virtual de la unidad. Estoy aquí para ayudarte con cualquier duda sobre tu tratamiento o medicación."

    # Urgencias: derivar inmediatamente
    palabras_urgencia = ["dolor fuerte", "sangre", "fiebre alta", "hinchado", "ahogo", "urgencia", "pecho"]
    if any(x in p for x in palabras_urgencia):
        return "⚠️ **DETECTADO SÍNTOMA DE ALERTA**\n\nComo asistente virtual no puedo valorar urgencias médicas. Por favor, acude al hospital o contacta con tu reumatólogo inmediatamente."

    # =========================================================================
    # 2. DOSIS OLVIDADAS - Respuestas específicas por medicamento
    # =========================================================================
    
    palabras_olvido = [
        "olvidé", "olvide", "olvidado", "perdí", "perdi", "perdido",
        "no me pinché", "no me pinche", "no tomé", "no tome",
        "salté", "salte", "saltado", "me la salté", "se me pasó",
        "ayer no", "no puse", "qué hago", "que hago", "me olvide"
    ]
    es_dosis_olvidada = any(x in p for x in palabras_olvido)
    
    if es_dosis_olvidada:
        # --- METOTREXATO ---
        if any(x in p for x in ["metotrexato", "metotrexate", "mtx"]):
            return """⚠️ **Dosis olvidada de Metotrexato**

**Regla general:** Si te olvidaste ayer, puedes ponértela hoy (dentro de las 48h siguientes al día pautado).

📌 **Recomendaciones:**
• Si han pasado **menos de 2 días**: Ponte la dosis hoy y sigue con tu calendario normal la próxima semana.
• Si han pasado **más de 2 días**: NO te pongas doble dosis. Salta esta semana y continúa la próxima según tu pauta habitual.

⚠️ **Importante:** Si tienes dudas o esto ocurre con frecuencia, consulta con tu reumatólogo.

💡 Consejo: Activa recordatorios en tu móvil para el día que te toca."""
        
        # --- ÁCIDO FÓLICO ---
        elif any(x in p for x in ["ácido fólico", "acido folico", "fólico", "folico", "acfol"]):
            return """💊 **Dosis olvidada de Ácido Fólico**

No te preocupes, el ácido fólico es un suplemento y no pasa nada grave si te saltas una dosis.

📌 **Recomendaciones:**
• Tómalo cuando te acuerdes si es el mismo día.
• Si ya pasó el día, simplemente continúa con la siguiente dosis programada.
• **Nunca tomes doble dosis** para compensar."""
        
        # --- ADALIMUMAB / HUMIRA ---
        elif any(x in p for x in ["humira", "adalimumab"]):
            return """💉 **Dosis olvidada de Humira/Adalimumab**

📌 **Recomendaciones:**
• Si te acuerdas **en los primeros días**, ponte la inyección cuanto antes.
• Luego, ajusta tu calendario para mantener el intervalo de 2 semanas.
• **No te pongas doble dosis.**

⚠️ Si tienes dudas, contacta con tu reumatólogo o enfermera de la unidad."""
        
        # --- GENÉRICO ---
        else:
            return """⚠️ **Dosis olvidada de medicación**

📌 **Regla general:**
• Si te acuerdas el mismo día o al día siguiente, tómala/ponla cuando te acuerdes.
• Si han pasado más de 2 días, **no tomes doble dosis**. Espera a la siguiente dosis programada.

⚠️ Si tienes dudas sobre tu medicamento específico, consulta con tu reumatólogo o llama a la unidad."""

    # =========================================================================
    # 3. MEDICACIÓN ACTUAL - Extraer del historial
    # =========================================================================
    
    palabras_medicacion = [
        "medicación", "medicacion", "medicamento", "tratamiento",
        "llevo", "tomo", "actual", "ahora", "qué tomo", "que tomo",
        "dosis", "pauta", "inyectar", "pinchar", "pastilla"
    ]
    es_pregunta_medicacion = any(x in p for x in palabras_medicacion)
    
    if es_pregunta_medicacion:
        ultimo_plan = None
        
        # Buscar el plan de tratamiento en la última visita
        if historial_paciente and len(historial_paciente) > 0:
            ultimo = historial_paciente[-1]
            if isinstance(ultimo, dict):
                plan_directo = ultimo.get("plan_tratamiento", "")
                if not plan_directo:
                    # Intentar extraer del curso clínico
                    curso = ultimo.get("curso_clinico_generado", "")
                    if "PLAN:" in curso:
                        plan_directo = curso.split("PLAN:")[-1].strip()
                    elif "Plan:" in curso:
                        plan_directo = curso.split("Plan:")[-1].strip()
                    else:
                        plan_directo = curso
                
                ultimo_plan = plan_directo
        
        if ultimo_plan:
            medicaciones = _extraer_medicaciones_del_plan(ultimo_plan)
            
            if medicaciones:
                respuesta = "💊 **Tu medicación actual:**\n\n"
                for med in medicaciones:
                    respuesta += f"• {med}\n"
                respuesta += "\n📅 Puedes ver el calendario en la pestaña 'Mi Calendario' para ver cuándo te toca cada medicación."
                return respuesta
            else:
                return f"📋 **Tu plan de tratamiento actual:**\n\n{ultimo_plan}"
        else:
            return "📋 No tienes ningún plan de tratamiento activo. Consulta con tu médico en la próxima visita."

    # =========================================================================
    # 4. CITAS - Información sobre gestión
    # =========================================================================
    
    if any(x in p for x in ["cita", "próxima visita", "proxima visita", "cuando tengo", "revisión", "revision"]):
        return "📅 Las citas se gestionan a través de la secretaría del hospital. Puedes llamar al teléfono de atención o consultar tu portal del paciente para ver tus próximas citas."

    # =========================================================================
    # 5. RAG - Consultar guías médicas para preguntas generales
    # =========================================================================
    
    respuesta_rag = "NO_CONTEXT"
    
    if RAG_DISPONIBLE:
        # Carga perezosa del vectorstore (solo la primera vez)
        if st.session_state.vectorstore_cache is None:
            with st.spinner("🔄 Consultando guías médicas..."):
                st.session_state.vectorstore_cache = cargar_conocimiento()
        
        if st.session_state.vectorstore_cache:
            try:
                raw_response = consultar_rag(st.session_state.vectorstore_cache, pregunta)
                
                if "NO_CONTEXT" not in raw_response and len(raw_response) > 5:
                    respuesta_rag = raw_response
            except Exception as e:
                print(f"Error RAG: {e}")
                respuesta_rag = "NO_CONTEXT"
    
    # Si el RAG encontró información relevante
    if respuesta_rag != "NO_CONTEXT":
        return f"📚 **Información general:**\n\n{respuesta_rag}"

    # =========================================================================
    # 6. FALLBACK - Derivar al médico
    # =========================================================================
    
    return "❓ No tengo información específica sobre eso. Si tienes dudas sobre tu tratamiento, te recomiendo consultarlo con tu médico en la próxima visita o llamar a la unidad."
