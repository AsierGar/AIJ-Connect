"""
================================================================================
UI_VISITA.PY - Formulario de Nueva Visita Médica
================================================================================

Este módulo implementa el formulario completo para registrar una visita médica
de un paciente con AIJ (Artritis Idiopática Juvenil).

SECCIONES DEL FORMULARIO:

1. RECOGIDA DE DATOS:
   - Datos biométricos: peso actual, talla, BSA
   - Exploración articular: homúnculo interactivo
   - Escalas clínicas: EVA médico, EVA paciente
   - Laboratorio: VSG (opcional)
   - Documentos adjuntos: analíticas, informes

2. PLAN DE TRATAMIENTO:
   - Cálculo automático JADAS-27
   - Entrada de texto libre del plan
   - Generación de curso clínico con IA (opcional)

3. VALIDACIÓN IA:
   - Análisis del plan con CrewAI
   - Verificación de dosis contra guías médicas
   - Alertas de seguridad farmacológica

4. GUARDAR VISITA:
   - Registro en historial del paciente
   - Actualización de datos del paciente
   - Guardado de documentos adjuntos

INTEGRACIÓN IA:
- Usa ai_backend/agents/tripulacion.py para validación
- RAG sobre fichas técnicas y guías de AIJ
- json_repair para manejar respuestas malformadas del LLM
================================================================================
"""

import streamlit as st
import json
import os
from datetime import date
import time
from data_manager import guardar_historial, guardar_paciente
import requests
from streamlit_lottie import st_lottie
import math
from json_repair import repair_json  # Para reparar JSON malformado del LLM

# Directorio para guardar PDFs subidos
PDF_UPLOAD_DIR = "mobile_app/documentos_pacientes"
os.makedirs(PDF_UPLOAD_DIR, exist_ok=True)

# --- IMPORTS OPCIONALES ---
try:
    from homunculo_visita import renderizar_homunculo
    HOMUNCULO_OK = True
except ImportError:
    HOMUNCULO_OK = False

try:
    from ai_backend.agents.tripulacion import ejecutar_validacion_medica
    IA_DISPONIBLE = True
except ImportError:
    IA_DISPONIBLE = False

# --- UTILS LOTTIE ---
def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

# ==============================================================================
# 🧠 CEREBRO DE LIMPIEZA CON JSON_REPAIR
# ==============================================================================
def limpiar_respuesta_ia(respuesta_obj):
    """
    Usa json_repair para extraer datos estructurados ignorando texto,
    markdown y errores de formato comunes de LLMs.
    """
    if respuesta_obj is None:
        return {"estado": "Error", "analisis": {}, "auditoria": {"razon": "No hay respuesta"}}

    def _normalizar_schema(obj):
        if not isinstance(obj, dict):
            return None

        # Schema esperado (estado/analisis/auditoria)
        if "analisis" in obj or "auditoria" in obj or "estado" in obj:
            return obj

        # Schema plano (tool output sin anidado)
        claves_planas = {
            "farmaco", "dosis_mg_kg", "dosis_mg_kg_detectada", "dosis_calculada",
            "frecuencia", "frecuencia_texto", "frecuencia_horas",
            "es_tratamiento_aij", "es_aij", "razon_decision", "razon"
        }
        if any(k in obj for k in claves_planas):
            es_aij = obj.get("es_aij")
            if es_aij is None:
                es_aij = obj.get("es_tratamiento_aij")

            analisis = {
                "farmaco": obj.get("farmaco"),
                "dosis_calculada": obj.get("dosis_calculada"),
                "dosis_mg_kg_detectada": obj.get("dosis_mg_kg_detectada", obj.get("dosis_mg_kg")),
                "frecuencia": obj.get("frecuencia", obj.get("frecuencia_texto")),
                "frecuencia_horas": obj.get("frecuencia_horas"),
            }
            auditoria = {
                "es_aij": es_aij,
                "es_tratamiento_aij": obj.get("es_tratamiento_aij"),
                "razon": obj.get("razon", obj.get("razon_decision")),
                "razon_decision": obj.get("razon_decision"),
            }
            estado = obj.get("estado")
            if not estado:
                estado = "Aprobada" if es_aij is True else "Alerta"
            return {
                "estado": estado,
                "analisis": analisis,
                "auditoria": auditoria,
                "decision": obj.get("decision") or obj.get("severidad"),
            }

        return obj

    # 1. Convertir a string sea lo que sea
    texto_raw = ""
    if isinstance(respuesta_obj, dict):
        normalizado = _normalizar_schema(respuesta_obj)
        if normalizado is not None:
            return normalizado
        return respuesta_obj
    elif hasattr(respuesta_obj, 'raw'):
        texto_raw = respuesta_obj.raw
    elif hasattr(respuesta_obj, 'json_dict') and respuesta_obj.json_dict:
        normalizado = _normalizar_schema(respuesta_obj.json_dict)
        if normalizado is not None:
            return normalizado
        return respuesta_obj.json_dict
    else:
        texto_raw = str(respuesta_obj)

    # 2. LA MAGIA: json_repair busca el objeto JSON válido dentro del texto sucio
    try:
        # return_objects=True hace que devuelva dicts/listas en vez de string
        objeto_reparado = repair_json(texto_raw, return_objects=True)

        # A veces devuelve una lista si el modelo puso [ ... ] o varios objetos
        if isinstance(objeto_reparado, list) and len(objeto_reparado) > 0:
            normalizado = _normalizar_schema(objeto_reparado[0])
            if normalizado is not None:
                return normalizado
            return objeto_reparado[0]  # Cogemos el primero
        elif isinstance(objeto_reparado, dict):
            normalizado = _normalizar_schema(objeto_reparado)
            if normalizado is not None:
                return normalizado
            return objeto_reparado

    except Exception as e:
        print(f"⚠️ Falló json_repair: {e}")

    # 3. FALLBACK DE EMERGENCIA (Si json_repair falla, mostramos texto)
    texto_limpio = texto_raw.replace("**", "").replace("```json", "").replace("```", "").strip()
    return {
        "estado": "Nota del Asistente",
        "analisis": {
            "farmaco": "Ver texto",
            "dosis_calculada": "-"
        },
        "auditoria": {
            "es_aij": None,
            "razon": texto_limpio
        }
    }

# ==============================================================================
# 🏥 RENDERIZADO VISITA
# ==============================================================================
def render_nueva_visita(paciente):
    lottie_medico = load_lottieurl("https://lottie.host/9e53063f-6316-4328-9366-41716922d579/F2jKkK7yqP.json")

    if "visita_step" not in st.session_state: st.session_state.visita_step = 1
    if "temp_visita_data" not in st.session_state: st.session_state.temp_visita_data = {}
    if "visita_arts" not in st.session_state: st.session_state.visita_arts = set()
    if "ia_validacion_hecha" not in st.session_state: st.session_state.ia_validacion_hecha = False
    if "ia_resultado_cache" not in st.session_state: st.session_state.ia_resultado_cache = None

    # --------------------------------------------------------------------------
    # PASO 1: RECOGIDA DE DATOS
    # --------------------------------------------------------------------------
    if st.session_state.visita_step == 1:
        
        c_anim, c_tit, c_close = st.columns([1, 5, 1], gap="small")
        with c_anim:
            if lottie_medico: st_lottie(lottie_medico, height=80, key="anim_doc")
            else: st.markdown("🩺")
        with c_tit:
            st.markdown(f"## Consulta: **{paciente['nombre']}**")
        with c_close:
            if st.button("❌", help="Cancelar", type="secondary"):
                st.session_state.modo_visita = False
                for k in ["visita_step", "temp_visita_data", "visita_arts", "ia_validacion_hecha", "ia_resultado_cache"]:
                    if k in st.session_state: del st.session_state[k]
                st.rerun()
        
        st.info(f"🆔 **NHC:** {paciente.get('id', '?')} | 🎂 **Edad:** {paciente.get('edad', '-')} | 🏷️ **Diag:** {paciente.get('diagnostico', '-')}")

        prev_data = st.session_state.temp_visita_data

        with st.container(border=True):
            st.markdown("### 1. 📏 Constantes y Anamnesis")
            c_peso, c_talla, c_bsa = st.columns(3)
            
            with c_peso:
                peso_val = prev_data.get("peso", paciente.get("peso_actual", 0.0))
                nuevo_peso = st.number_input("Peso (kg)", 0.0, 150.0, float(peso_val), step=0.1)
            
            with c_talla:
                # Buscar talla en ambos campos posibles
                talla_val = prev_data.get("talla") or paciente.get("talla_actual") or paciente.get("talla") or 100
                nueva_talla = st.number_input("Altura (cm)", 0, 250, int(talla_val), step=1)

            with c_bsa:
                bsa = 0.0
                if nuevo_peso > 0 and nueva_talla > 0:
                    bsa = math.sqrt((nuevo_peso * nueva_talla) / 3600)
                    st.metric("BSA (m²)", f"{bsa:.2f}")
                else:
                    st.metric("BSA (m²)", "-")

            st.divider()
            anamnesis = st.text_area("Evolución clínica:", height=100, value=prev_data.get("anamnesis", ""))

        with st.container(border=True):
            st.markdown("### 2. 🩺 Exploración Física")
            if not st.session_state.visita_arts and "arts_activas" in prev_data:
                 st.session_state.visita_arts = set(prev_data["arts_activas"])

            col_img, col_datos = st.columns([1, 1])

            with col_img:
                # Marco estilizado para el homúnculo
                st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border-radius: 12px;
                        padding: 15px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                        border: 1px solid #dee2e6;
                    ">
                        <p style="text-align:center; color:#C41E3A; font-weight:600; margin-bottom:10px;">
                            🦴 Mapa Articular
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                st.caption("👆 Clica en las articulaciones afectadas")
                if HOMUNCULO_OK:
                    st.session_state.visita_arts = renderizar_homunculo(st.session_state.visita_arts, key_suffix="visita_main")
                else:
                    st.error("Error componente")

            with col_datos:
                st.write("**Seleccionadas:**")
                lista_actual = sorted(list(st.session_state.visita_arts))
                sel = st.pills("Arts", lista_actual, selection_mode="multi", default=lista_actual, key=f"pills_{len(lista_actual)}")
                if len(sel) < len(lista_actual):
                    st.session_state.visita_arts = set(sel)
                    st.rerun()
                
                if not lista_actual: st.caption("Ninguna")
                st.divider()
                
                nat_c = len(st.session_state.visita_arts)
                c_nad, c_nat = st.columns(2)
                nad = c_nad.number_input("NAD", 0, 71, value=prev_data.get("nad", 0))
                nat = c_nat.number_input("NAT", 0, 71, value=max(nat_c, prev_data.get("nat", 0)))
                
                st.divider()
                c_eva1, c_eva2 = st.columns(2)
                with c_eva1:
                    eva = st.slider("EVA Médico", 0.0, 10.0, value=float(prev_data.get("eva", 0.0)), step=0.5)
                with c_eva2:
                    eva_paciente = st.slider("EVA Paciente/Familia", 0.0, 10.0, value=float(prev_data.get("eva_paciente", 0.0)), step=0.5, help="Valoración del dolor por el paciente o familia")

        with st.container(border=True):
            st.markdown("### 3. 🧪 Analítica")
            ana = prev_data.get("analitica", {})
            c1, c2, c3, c4 = st.columns(4)
            hb = c1.text_input("Hb (g/dL)", value=ana.get("hb",""))
            vsg = c2.text_input("VSG (mm/h)", value=ana.get("vsg",""))
            pcr = c3.text_input("PCR (mg/L)", value=ana.get("pcr",""))
            calpro = c4.text_input("Calprotectina (µg/g)", value=ana.get("calpro",""), help="Calprotectina sérica")
        
        with st.container(border=True):
            st.markdown("### 4. 🖼️ Pruebas Complementarias")
            pruebas = st.text_area("Descripción pruebas de imagen:", height=60, value=prev_data.get("pruebas",""))
            
            st.markdown("---")
            st.markdown("**📎 Adjuntar documentos (analíticas, informes previos...)**")
            uploaded_files = st.file_uploader(
                "Subir PDF o imagen",
                type=["pdf", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
                key="docs_visita"
            )
            
            # Mostrar archivos ya subidos en esta sesión
            if "archivos_subidos" not in st.session_state:
                st.session_state.archivos_subidos = []
            
            if uploaded_files:
                for uf in uploaded_files:
                    if uf.name not in [f["nombre"] for f in st.session_state.archivos_subidos]:
                        st.session_state.archivos_subidos.append({
                            "nombre": uf.name,
                            "tipo": uf.type,
                            "contenido": uf.read()
                        })
                        uf.seek(0)  # Reset para posible relectura
                
            if st.session_state.archivos_subidos:
                st.caption(f"📄 {len(st.session_state.archivos_subidos)} archivo(s) adjuntado(s):")
                for f in st.session_state.archivos_subidos:
                    st.text(f"  • {f['nombre']}")

        st.markdown("###")
        
        if st.button("➡️ Siguiente Paso", type="primary", use_container_width=True):
            st.session_state.temp_visita_data = {
                "peso": nuevo_peso, "talla": nueva_talla, "bsa": round(bsa, 2),
                "anamnesis": anamnesis, "nad": nad, "nat": nat, "eva": eva,
                "eva_paciente": eva_paciente,
                "arts_activas": list(st.session_state.visita_arts),
                "analitica": {"hb": hb, "vsg": vsg, "pcr": pcr, "calpro": calpro},
                "pruebas": pruebas,
                "archivos_adjuntos": st.session_state.get("archivos_subidos", [])
            }
            st.session_state.visita_step = 2
            st.rerun()

    # --------------------------------------------------------------------------
    # PASO 2: PLAN
    # --------------------------------------------------------------------------
    elif st.session_state.visita_step == 2:
        st.markdown("## 💊 Plan Terapéutico")
        data = st.session_state.temp_visita_data
        
        with st.expander("👁️ Ver Resumen Clínico", expanded=False):
            c_r1, c_r2, c_r3, c_r4 = st.columns(4)
            c_r1.metric("Peso", f"{data.get('peso')} kg")
            c_r2.metric("BSA", f"{data.get('bsa')} m²")
            c_r3.metric("NAT", data.get('nat', 0))
            
            # Calcular JADAS
            ana = data.get("analitica", {})
            vsg_val = None
            pcr_val = None
            try:
                vsg_val = float(ana.get("vsg", "").replace(",", ".")) if ana.get("vsg") else None
            except: pass
            try:
                pcr_val = float(ana.get("pcr", "").replace(",", ".")) if ana.get("pcr") else None
            except: pass
            
            # Importar función JADAS del dashboard
            try:
                from ui_dashboard import calcular_jadas
                jadas = calcular_jadas(
                    nad=data.get("nad", 0),
                    eva_medico=data.get("eva", 0),
                    eva_paciente=data.get("eva_paciente", 0),
                    vsg=vsg_val,
                    pcr=pcr_val
                )
                interp, emoji = jadas["interpretacion"]
                c_r4.metric(f"JADAS-27 {emoji}", f"{jadas['total']}", delta=interp, delta_color="off")
            except:
                c_r4.metric("JADAS-27", "-")
            
            st.write(f"**Anamnesis:** {data.get('anamnesis')}")
            st.write(f"**Activas:** {', '.join(data.get('arts_activas', []))}")
            
            # Mostrar archivos adjuntos
            archivos = data.get("archivos_adjuntos", [])
            if archivos:
                st.write(f"**📎 Documentos adjuntos:** {len(archivos)} archivo(s)")

        # --- EFECTOS ADVERSOS ---
        with st.container(border=True):
            st.markdown("### ⚠️ Efectos Adversos")
            st.caption("Registrar cualquier efecto secundario de la medicación actual")
            
            # Efectos adversos comunes por medicación
            EFECTOS_COMUNES = {
                "MTX/Metotrexato": ["Náuseas/Vómitos", "Mucositis oral", "Elevación transaminasas", "Cefalea", "Astenia", "Alopecia"],
                "AINEs": ["Dolor abdominal", "Pirosis/Reflujo", "Náuseas"],
                "Corticoides": ["Aumento peso", "Hiperglucemia", "Cambios humor", "Insomnio", "Acné", "Cushing"],
                "Biológicos": ["Reacción infusión/inyección", "Infección respiratoria", "Infección urinaria", "Cefalea", "Fiebre"]
            }
            
            efectos_previos = data.get("efectos_adversos", [])
            
            c_med, c_efecto = st.columns([1, 2])
            with c_med:
                tipo_med = st.selectbox("Medicación", list(EFECTOS_COMUNES.keys()) + ["Otro"])
            
            with c_efecto:
                if tipo_med != "Otro":
                    efectos_opciones = EFECTOS_COMUNES.get(tipo_med, [])
                    efectos_sel = st.multiselect("Efectos observados", efectos_opciones + ["Otro (especificar)"], default=[])
                else:
                    efectos_sel = []
            
            c_desc, c_grav = st.columns([2, 1])
            with c_desc:
                descripcion_efecto = st.text_input("Descripción/Detalles", placeholder="Describir efecto adverso...")
            with c_grav:
                gravedad = st.selectbox("Gravedad", ["Leve", "Moderado", "Grave"])
            
            # Guardar efectos en session_state
            if "efectos_visita" not in st.session_state:
                st.session_state.efectos_visita = efectos_previos.copy() if efectos_previos else []
            
            if st.button("➕ Añadir efecto adverso", use_container_width=True):
                if efectos_sel or descripcion_efecto:
                    nuevo_efecto = {
                        "fecha": date.today().strftime("%Y-%m-%d"),
                        "medicacion": tipo_med,
                        "efectos": efectos_sel,
                        "descripcion": descripcion_efecto,
                        "gravedad": gravedad
                    }
                    st.session_state.efectos_visita.append(nuevo_efecto)
                    st.success("✓ Efecto registrado")
            
            # Mostrar efectos registrados en esta visita
            if st.session_state.efectos_visita:
                st.markdown("---")
                st.caption("**Efectos registrados en esta visita:**")
                for i, ef in enumerate(st.session_state.efectos_visita):
                    color = "🔴" if ef["gravedad"] == "Grave" else ("🟠" if ef["gravedad"] == "Moderado" else "🟡")
                    efectos_txt = ", ".join(ef["efectos"]) if ef["efectos"] else ef["descripcion"]
                    st.markdown(f"{color} **{ef['medicacion']}**: {efectos_txt} ({ef['gravedad']})")
        
        with st.container(border=True):
            st.markdown("### Pauta y Recomendaciones")
            col_plan, col_ia = st.columns([2, 1])
            
            with col_plan:
                plan_input = st.text_area("Plan detallado:", height=200, key="plan_final")
            
            with col_ia:
                st.info("💡 Asistente IA")
                if st.button("✨ Validar", type="primary", use_container_width=True):
                    st.session_state.ia_validacion_hecha = True
                    if IA_DISPONIBLE:
                        with st.spinner("🤖 Consultando guías médicas..."):
                            peso_calculo = data.get('peso', 30.0)
                            try:
                                res = ejecutar_validacion_medica(plan_input, peso_calculo, paciente['id'])
                                st.session_state.ia_resultado_cache = limpiar_respuesta_ia(res)
                            except Exception as e:
                                st.session_state.ia_resultado_cache = {
                                    "estado": "Error",
                                    "analisis": {},
                                    "auditoria": {"es_aij": None, "razon": f"Error: {e}"}
                                }
                    else:
                        st.session_state.ia_resultado_cache = {"estado": "Offline"}

        if st.session_state.ia_validacion_hecha:
            res = st.session_state.ia_resultado_cache
            
            with st.container(border=True):
                def _coerce_text(value, default="-"):
                    if value is None:
                        return default
                    if isinstance(value, (dict, list)):
                        return json.dumps(value, ensure_ascii=False)
                    return str(value)

                def _es_rechazo_por_texto(razon_texto):
                    texto = (razon_texto or "").lower()
                    palabras = [
                        "contraind", "contraindicad", "no indicado", "no indicada",
                        "no recomendado", "no recomendada", "no usar", "no se recomienda",
                        "toxic", "toxicidad", "sobredos", "sobredosis", "dosis alta",
                        "dosis excesiva", "exceso", "excesiva"
                    ]
                    return any(p in texto for p in palabras)

                # --- LÓGICA DE VISUALIZACIÓN ---
                estado = res.get("estado", "Desconocido")
                analisis = res.get("analisis", {})
                auditoria = res.get("auditoria", {})
                
                # Buscamos la validación en varios sitios posibles
                es_valido = False
                if estado == "Aprobada": es_valido = True
                if auditoria.get("es_tratamiento_aij") is True: es_valido = True
                if auditoria.get("es_aij") is True: es_valido = True

                decision_raw = res.get("decision") or res.get("severidad") or auditoria.get("decision")
                decision_txt = _coerce_text(decision_raw, default="").strip().lower()

                decision = None
                if "aprob" in decision_txt:
                    decision = "Aprobada"
                elif "rech" in decision_txt:
                    decision = "Rechazada"
                elif "alert" in decision_txt:
                    decision = "Alerta"

                if decision is None:
                    if es_valido:
                        decision = "Aprobada"
                    else:
                        razon_texto = _coerce_text(
                            auditoria.get("razon_decision")
                            or auditoria.get("razon")
                            or res.get("razon_decision")
                            or res.get("razon")
                            or ""
                        )
                        decision = "Rechazada" if _es_rechazo_por_texto(razon_texto) else "Alerta"

                # Título de la tarjeta
                if decision == "Aprobada":
                    st.success("✅ **PLAN VALIDADO**")
                elif decision == "Rechazada":
                    st.error("⛔ **PLAN RECHAZADO**")
                else:
                    st.warning("⚠️ **ALERTA DE SEGURIDAD**")

                # Contenido (Columnas)
                c_izq, c_der = st.columns([1, 1])
                with c_izq:
                    st.markdown("**Análisis Dosis:**")
                    farmaco = _coerce_text(analisis.get("farmaco") or res.get("farmaco"))
                    dosis_mg_kg = analisis.get("dosis_mg_kg") or analisis.get("dosis_mg_kg_detectada") or res.get("dosis_mg_kg") or res.get("dosis_mg_kg_detectada")
                    dosis_calc = analisis.get("dosis_calculada") or res.get("dosis_calculada")
                    frecuencia = analisis.get("frecuencia") or analisis.get("frecuencia_texto") or res.get("frecuencia") or res.get("frecuencia_texto")

                    dosis_txt = _coerce_text(dosis_mg_kg, default=None)
                    if dosis_txt and "mg/kg" not in dosis_txt.lower():
                        dosis_txt = f"{dosis_txt} mg/kg"
                    if not dosis_txt:
                        dosis_txt = _coerce_text(dosis_calc)

                    st.write(f"💊 Fármaco: **{farmaco}**")
                    st.write(f"⚖️ Dosis: **{dosis_txt}**")
                    if frecuencia:
                        st.write(f"🕒 Frecuencia: **{_coerce_text(frecuencia)}**")
                
                with c_der:
                    st.markdown("**Dictamen:**")
                    razon = auditoria.get("razon_decision") or auditoria.get("razon") or res.get("razon_decision") or res.get("razon") or "Sin comentarios."
                    st.write(_coerce_text(razon))

                with st.expander("Ver auditoría IA"):
                    st.write(f"Decisión: **{decision}**")
                    st.write(f"Fármaco: **{farmaco}**")
                    st.write(f"Dosis: **{dosis_txt}**")
                    if frecuencia:
                        st.write(f"Frecuencia: **{_coerce_text(frecuencia)}**")
                    origen = "Fallback" if "fallback" in _coerce_text(razon).lower() else "Agente"
                    st.write(f"Origen: **{origen}**")
                    st.write(f"Motivo: {_coerce_text(razon)}")

            c_back, c_save = st.columns([1, 3])
            if c_back.button("⬅️ Editar"):
                st.session_state.ia_validacion_hecha = False
                st.rerun()
                
            if c_save.button("💾 CONFIRMAR Y GUARDAR", type="primary", use_container_width=True):
                fecha_hoy = date.today().strftime("%Y-%m-%d")
                
                nuevo_peso = data.get("peso")
                if nuevo_peso > 0:
                    paciente["peso_actual"] = nuevo_peso
                    if "historial_peso" not in paciente: paciente["historial_peso"] = {}
                    paciente["historial_peso"][fecha_hoy] = nuevo_peso
                
                nueva_talla = data.get("talla")
                print(f"📏 Talla a guardar: {nueva_talla} (tipo: {type(nueva_talla)})")
                if nueva_talla and nueva_talla > 0:
                    paciente["talla"] = nueva_talla  # Campo original del alta
                    paciente["talla_actual"] = nueva_talla  # Campo de visita
                    if "historial_talla" not in paciente: paciente["historial_talla"] = {}
                    paciente["historial_talla"][fecha_hoy] = nueva_talla
                    print(f"✅ Talla guardada: {paciente['historial_talla']}")

                arts_str = ", ".join(data.get("arts_activas", []))
                eva_med = data.get('eva', 0)
                eva_pac = data.get('eva_paciente', 0)
                curso = f"FECHA: {fecha_hoy}\nPESO: {nuevo_peso}kg | BSA: {data.get('bsa')}m²\nEVA: {eva_med}/10 (médico) | {eva_pac}/10 (paciente)\nANAMNESIS: {data.get('anamnesis')}\nEXPLORACIÓN: {arts_str}\nPLAN: {plan_input}"
                
                paciente["ultimo_curso_clinico"] = curso
                guardar_paciente(paciente)
                
                # Guardar archivos adjuntos
                archivos_guardados = []
                archivos_adjuntos = data.get("archivos_adjuntos", [])
                if archivos_adjuntos:
                    dir_paciente = os.path.join(PDF_UPLOAD_DIR, paciente["id"])
                    os.makedirs(dir_paciente, exist_ok=True)
                    
                    for archivo in archivos_adjuntos:
                        nombre_archivo = f"{fecha_hoy}_{archivo['nombre']}"
                        ruta_archivo = os.path.join(dir_paciente, nombre_archivo)
                        with open(ruta_archivo, "wb") as f:
                            f.write(archivo["contenido"])
                        archivos_guardados.append(nombre_archivo)
                        print(f"📎 Archivo guardado: {ruta_archivo}")
                
                nueva_visita = {
                    "fecha": fecha_hoy, "tipo": "Seguimiento",
                    "anamnesis": data.get('anamnesis'),
                    "datos_basicos": {"peso": nuevo_peso, "talla": data.get("talla"), "bsa": data.get("bsa")},
                    "exploracion": data, "analitica": data.get('analitica'),
                    "eva_paciente": eva_pac,
                    "plan_tratamiento": plan_input, "curso_clinico_generado": curso,
                    "auditoria_ia": st.session_state.ia_resultado_cache,
                    "documentos_adjuntos": archivos_guardados,
                    "efectos_adversos": st.session_state.get("efectos_visita", [])
                }
                guardar_historial(paciente["id"], nueva_visita)
                
                # Limpiar archivos subidos de la sesión
                st.session_state.archivos_subidos = []
                
                st.success("✅ Guardado correctamente")
                time.sleep(1.5)
                st.session_state.modo_visita = False
                st.rerun()
        else:
            st.markdown("---")
            if st.button("⬅️ Atrás"):
                st.session_state.visita_step = 1
                st.rerun()