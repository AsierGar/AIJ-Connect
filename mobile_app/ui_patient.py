"""
================================================================================
UI_PATIENT.PY - Portal del Paciente
================================================================================

Este módulo implementa la vista del paciente, diseñada para que los pacientes
(o sus padres) puedan consultar información sobre su tratamiento.

FUNCIONALIDADES:

1. MI CALENDARIO:
   - Calendario interactivo con eventos de medicación
   - Generación automática de eventos según el plan de tratamiento
   - Colores por tipo de medicación (inyectables, orales, suplementos)
   - Vista mensual con navegación

2. CHAT DE AYUDA:
   - Chatbot para resolver dudas sobre medicación
   - Respuestas específicas para dosis olvidadas
   - Integración con RAG para consultas a guías médicas
   - Guardrails de seguridad para derivar urgencias

3. MIS FOTOS:
   - Galería de fotos clínicas subidas en visitas
   - Organización cronológica por fecha y zona

GENERACIÓN DE EVENTOS:
El calendario analiza el plan de tratamiento y genera eventos automáticos:
- Metotrexato: evento semanal el día indicado
- Ácido fólico: eventos diarios o según pauta
- Biológicos: eventos quincenales/mensuales
- AINEs: eventos diarios

COMPONENTES EXTERNOS:
- streamlit-calendar: Calendario interactivo tipo FullCalendar
================================================================================
"""

import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from patient_bot import responder_duda_paciente
from data_manager import cargar_historial_medico

# --- MOTOR DE REGLAS MEJORADO ---
def _detectar_dia_semana(texto):
    """Detecta qué día de la semana se menciona en el texto."""
    dias_map = {
        "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
        "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
    }
    texto_lower = texto.lower()
    for dia_nombre, dia_num in dias_map.items():
        if dia_nombre in texto_lower:
            return dia_num
    return None

def _extraer_dosis(texto, medicamento):
    """Intenta extraer la dosis de un medicamento del texto."""
    import re
    texto_lower = texto.lower()
    # Buscar patrón: medicamento + número + mg
    patron = rf"{medicamento.lower()}[^\d]*(\d+(?:[.,]\d+)?)\s*mg"
    match = re.search(patron, texto_lower)
    if match:
        return match.group(1) + "mg"
    return ""

def _generar_eventos_desde_texto(plan_texto):
    """
    Analiza el texto del médico y genera eventos de calendario dinámicos.
    Detecta días específicos mencionados (lunes, martes, etc.)
    Si detecta "crónico" o "indefinido", genera eventos para 1 año.
    """
    if not plan_texto: 
        return [], []
        
    texto_lower = plan_texto.lower()
    eventos = []
    meds_detectados = []
    fecha_base = datetime.today()
    
    # Detectar si es tratamiento crónico
    es_cronico = any(palabra in texto_lower for palabra in ["crónico", "cronico", "indefinido", "mantenimiento", "de por vida"])
    
    # Configuración de medicamentos con sus variantes y colores
    medicamentos_config = {
        "metotrexato": {
            "variantes": ["metotrexato", "metotrexate", "mtx"],
            "icono": "💉",
            "color": "#C41E3A",  # Rojo granate
            "dia_defecto": 0,  # Lunes por defecto
            "frecuencia": "semanal"
        },
        "acido_folico": {
            "variantes": ["ácido fólico", "acido folico", "ac fólico", "ac folico", "acfol", "ácido folínico", "folinato"],
            "icono": "💊",
            "color": "#38A169",  # Verde
            "dia_defecto": 1,  # Martes por defecto (48h post-MTX)
            "frecuencia": "semanal"
        },
        "ibuprofeno": {
            "variantes": ["ibuprofeno", "ibuprofen"],
            "icono": "💊",
            "color": "#3182CE",  # Azul
            "dia_defecto": None,  # Diario
            "frecuencia": "diario",
            "duracion_dias": 7
        },
        "naproxeno": {
            "variantes": ["naproxeno"],
            "icono": "💊",
            "color": "#3182CE",
            "dia_defecto": None,
            "frecuencia": "diario",
            "duracion_dias": 7
        },
        "prednisona": {
            "variantes": ["prednisona", "prednisone", "corticoide"],
            "icono": "💊",
            "color": "#D69E2E",  # Amarillo
            "dia_defecto": None,
            "frecuencia": "diario",
            "duracion_dias": 14
        },
        "adalimumab": {
            "variantes": ["adalimumab", "humira"],
            "icono": "💉",
            "color": "#805AD5",  # Morado
            "dia_defecto": None,
            "frecuencia": "quincenal"
        },
        "tocilizumab": {
            "variantes": ["tocilizumab", "actemra"],
            "icono": "💉",
            "color": "#DD6B20",  # Naranja
            "dia_defecto": None,
            "frecuencia": "quincenal"
        },
    }
    
    # Procesar cada medicamento
    for med_key, config in medicamentos_config.items():
        # Verificar si el medicamento está en el texto
        encontrado = False
        for variante in config["variantes"]:
            if variante in texto_lower:
                encontrado = True
                break
        
        if not encontrado:
            continue
            
        # Extraer dosis si es posible
        dosis = ""
        for variante in config["variantes"]:
            dosis = _extraer_dosis(texto_lower, variante)
            if dosis:
                break
        
        nombre_display = med_key.replace("_", " ").title()
        meds_detectados.append(nombre_display)
        
        # Buscar si hay un día específico mencionado cerca del medicamento
        dia_especifico = None
        for variante in config["variantes"]:
            if variante in texto_lower:
                # Buscar contexto alrededor del medicamento
                idx = texto_lower.find(variante)
                contexto = texto_lower[idx:idx+100]  # 100 chars después
                dia_especifico = _detectar_dia_semana(contexto)
                if dia_especifico is not None:
                    break
        
        # Usar día específico o el por defecto
        dia_semana = dia_especifico if dia_especifico is not None else config["dia_defecto"]
        
        # Determinar duración: 365 días si es crónico, 60 días si no
        dias_a_generar = 365 if es_cronico else 60
        
        # Generar eventos según frecuencia
        if config["frecuencia"] == "semanal" and dia_semana is not None:
            for i in range(dias_a_generar):
                dia = fecha_base + timedelta(days=i)
                if dia.weekday() == dia_semana:
                    titulo = f"{config['icono']} {nombre_display}"
                    if dosis:
                        titulo += f" {dosis}"
                    eventos.append({
                        "title": titulo,
                        "start": dia.strftime("%Y-%m-%d"),
                        "backgroundColor": config["color"],
                        "borderColor": config["color"]
                    })
                    
        elif config["frecuencia"] == "diario":
            # Para diario, solo usar duración larga si es crónico
            if es_cronico:
                duracion = dias_a_generar
            else:
                duracion = config.get("duracion_dias", 7)
            for i in range(duracion):
                dia = fecha_base + timedelta(days=i)
                titulo = f"{config['icono']} {nombre_display}"
                if dosis:
                    titulo += f" {dosis}"
                eventos.append({
                    "title": titulo,
                    "start": dia.strftime("%Y-%m-%d"),
                    "backgroundColor": config["color"],
                    "borderColor": config["color"]
                })
                
        elif config["frecuencia"] == "quincenal":
            for i in range(dias_a_generar):
                dia = fecha_base + timedelta(days=i)
                if i % 14 == 0:
                    titulo = f"{config['icono']} {nombre_display}"
                    if dosis:
                        titulo += f" {dosis}"
                    eventos.append({
                        "title": titulo,
                        "start": dia.strftime("%Y-%m-%d"),
                        "backgroundColor": config["color"],
                        "borderColor": config["color"]
                    })

    return eventos, meds_detectados

def render_vista_paciente(paciente):
    # Cargar historial real
    historial = cargar_historial_medico(paciente["id"])
    
    # Obtener el ÚLTIMO plan escrito por el médico
    ultimo_plan_txt = ""
    if historial:
        ultimo_obj = historial[-1]
        if isinstance(ultimo_obj, dict):
            # Primero intentamos el campo directo plan_tratamiento
            plan_directo = ultimo_obj.get("plan_tratamiento", "")
            
            # Si está vacío, buscamos en curso_clinico_generado
            if not plan_directo:
                curso = ultimo_obj.get("curso_clinico_generado", "")
                # Extraer la parte después de "PLAN:" si existe
                if "PLAN:" in curso:
                    plan_directo = curso.split("PLAN:")[-1].strip()
                elif "Plan:" in curso:
                    plan_directo = curso.split("Plan:")[-1].strip()
                else:
                    plan_directo = curso  # Usar todo el texto como fallback
            
            ultimo_plan_txt = plan_directo
    
    # DEBUG: Ver qué texto está llegando
    print(f"📋 Plan detectado: '{ultimo_plan_txt[:200] if ultimo_plan_txt else 'VACÍO'}'")
    
    # Generar eventos DINÁMICOS basados en ese texto
    eventos_calendario, medicaciones_hoy = _generar_eventos_desde_texto(ultimo_plan_txt)
    
    print(f"📅 Eventos generados: {len(eventos_calendario)}, Meds: {medicaciones_hoy}")

    # --- UI ---
    st.image("https://cdn-icons-png.flaticon.com/512/3050/3050525.png", width=60)
    st.markdown(f"### Hola, **{paciente['nombre'].split()[0]}** 👋")
    
    if not ultimo_plan_txt:
        st.warning("⚠️ No tienes ningún plan de tratamiento activo.")
    
    tab_cal, tab_chaq, tab_fotos, tab_chat, tab_info = st.tabs(["📅 Mi Calendario", "📋 Cuestionario", "📷 Fotos", "💬 Asistente IA", "📄 Mis Informes"])
    
    # ==========================================================================
    # 📅 TAB 1: CALENDARIO DINÁMICO
    # ==========================================================================
    with tab_cal:
        if eventos_calendario:
            st.success(f"✅ Calendario sincronizado con tu último informe. ({len(eventos_calendario)} eventos)")
        else:
            st.info("No se han detectado medicamentos programados en tu último informe.")
            # Debug: mostrar qué texto se está leyendo
            with st.expander("🔍 Debug: Plan leído"):
                st.code(ultimo_plan_txt if ultimo_plan_txt else "Sin plan de tratamiento")

        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
            "initialView": "dayGridMonth",
            "selectable": True,
        }
        
        calendar(events=eventos_calendario, options=calendar_options, key="cal_paciente_dyn")
        
        st.markdown("###")
        
        # --- CHECKBOXES DINÁMICOS ---
        # Solo mostramos checkbox si HOY hay un evento para esa medicación
        with st.expander("✅ Registrar toma de hoy", expanded=True):
            hoy_str = datetime.today().strftime("%Y-%m-%d")
            
            # Buscamos qué toca HOY
            tareas_hoy = [e["title"] for e in eventos_calendario if e["start"] == hoy_str]
            
            if not tareas_hoy:
                st.caption("🎉 Hoy no tienes medicación programada.")
            else:
                for tarea in tareas_hoy:
                    st.checkbox(tarea, value=False, key=f"chk_{tarea}")
                
                if st.button("Guardar Registro", type="primary"):
                    st.toast("¡Toma registrada correctamente!")

    # ==========================================================================
    # 📋 TAB 2: CUESTIONARIO CHAQ
    # ==========================================================================
    with tab_chaq:
        st.markdown("##### 📋 Cuestionario CHAQ")
        st.caption("Completa este cuestionario antes de tu próxima visita. Ayuda al médico a evaluar tu estado.")
        
        # CHAQ simplificado (8 dominios)
        CHAQ_DOMINIOS = {
            "Vestirse y asearse": [
                "Vestirse, incluyendo atarse los zapatos y abrocharse botones",
                "Lavarse el pelo",
                "Quitarse los calcetines",
                "Cortarse las uñas"
            ],
            "Levantarse": [
                "Levantarse de una silla baja o del suelo",
                "Meterse y salir de la cama o ponerse de pie en la cuna"
            ],
            "Comer": [
                "Cortar su propia carne",
                "Llevarse un vaso o taza a la boca",
                "Abrir una caja de cereales nueva"
            ],
            "Caminar": [
                "Caminar en terreno llano",
                "Subir 5 escalones"
            ],
            "Higiene": [
                "Lavarse y secarse todo el cuerpo",
                "Sentarse y levantarse del retrete",
                "Cepillarse los dientes"
            ],
            "Alcanzar": [
                "Coger un objeto pesado por encima de la cabeza",
                "Agacharse a recoger ropa del suelo"
            ],
            "Agarrar": [
                "Abrir la puerta de un coche",
                "Abrir tarros ya abiertos",
                "Abrir y cerrar grifos",
                "Hacer recados e ir de compras"
            ],
            "Actividades": [
                "Hacer recados e ir de compras",
                "Meterse y salir del coche o autobús",
                "Montar en bicicleta o triciclo",
                "Hacer tareas de casa (limpiar, ordenar)"
            ]
        }
        
        OPCIONES_RESPUESTA = {
            "Sin ninguna dificultad": 0,
            "Con alguna dificultad": 1,
            "Con mucha dificultad": 2,
            "No puede hacerlo": 3
        }
        
        # Cargar respuestas previas si existen
        if "chaq_respuestas" not in st.session_state:
            st.session_state.chaq_respuestas = {}
        
        # Mostrar cuestionario
        total_score = 0
        num_preguntas = 0
        
        for dominio, preguntas in CHAQ_DOMINIOS.items():
            with st.expander(f"**{dominio}**", expanded=False):
                max_dominio = 0
                for pregunta in preguntas:
                    key = f"chaq_{dominio}_{pregunta[:20]}"
                    prev_val = st.session_state.chaq_respuestas.get(key, "Sin ninguna dificultad")
                    
                    respuesta = st.radio(
                        pregunta,
                        options=list(OPCIONES_RESPUESTA.keys()),
                        index=list(OPCIONES_RESPUESTA.keys()).index(prev_val) if prev_val in OPCIONES_RESPUESTA else 0,
                        horizontal=True,
                        key=key
                    )
                    
                    st.session_state.chaq_respuestas[key] = respuesta
                    score = OPCIONES_RESPUESTA[respuesta]
                    max_dominio = max(max_dominio, score)
                
                total_score += max_dominio
                num_preguntas += 1
        
        st.markdown("---")
        
        # Calcular score CHAQ (0-3, promedio de dominios)
        chaq_score = total_score / 8 if num_preguntas > 0 else 0
        
        col_score, col_interp = st.columns(2)
        with col_score:
            st.metric("Score CHAQ", f"{chaq_score:.2f}", help="0 = sin discapacidad, 3 = discapacidad severa")
        
        with col_interp:
            if chaq_score == 0:
                st.success("✅ Sin discapacidad funcional")
            elif chaq_score < 0.5:
                st.success("🟢 Discapacidad mínima")
            elif chaq_score < 1.0:
                st.warning("🟡 Discapacidad leve")
            elif chaq_score < 2.0:
                st.warning("🟠 Discapacidad moderada")
            else:
                st.error("🔴 Discapacidad severa")
        
        # EVA dolor del paciente
        st.markdown("---")
        st.markdown("**¿Cuánto dolor has tenido esta semana?**")
        eva_dolor = st.slider("EVA Dolor (0 = sin dolor, 10 = máximo dolor)", 0.0, 10.0, 0.0, 0.5)
        
        st.markdown("**¿Cómo valoras tu estado general esta semana?**")
        eva_global = st.slider("EVA Global (0 = muy bien, 10 = muy mal)", 0.0, 10.0, 0.0, 0.5)
        
        if st.button("💾 Guardar Cuestionario", type="primary", use_container_width=True):
            # Guardar en el historial del paciente
            from data_manager import guardar_paciente
            from datetime import date
            
            if "cuestionarios_chaq" not in paciente:
                paciente["cuestionarios_chaq"] = []
            
            nuevo_chaq = {
                "fecha": date.today().strftime("%Y-%m-%d"),
                "score": round(chaq_score, 2),
                "eva_dolor": eva_dolor,
                "eva_global": eva_global,
                "respuestas": dict(st.session_state.chaq_respuestas)
            }
            
            paciente["cuestionarios_chaq"].append(nuevo_chaq)
            guardar_paciente(paciente)
            
            st.success("✅ ¡Cuestionario guardado! Tu médico lo verá en la próxima visita.")
            st.balloons()
    
    # ==========================================================================
    # 📷 TAB 3: REGISTRO FOTOGRÁFICO
    # ==========================================================================
    with tab_fotos:
        st.markdown("##### 📷 Registro Fotográfico")
        st.caption("Sube fotos de las articulaciones afectadas para que tu médico pueda ver la evolución.")
        
        import os
        from datetime import date
        
        # Selector de articulación
        articulaciones_comunes = [
            "Rodilla derecha", "Rodilla izquierda",
            "Tobillo derecho", "Tobillo izquierdo",
            "Muñeca derecha", "Muñeca izquierda",
            "Codo derecho", "Codo izquierdo",
            "Manos", "Pies", "Otra"
        ]
        
        col_art, col_nota = st.columns(2)
        with col_art:
            articulacion = st.selectbox("Articulación", articulaciones_comunes)
        with col_nota:
            nota_foto = st.text_input("Nota/Comentario", placeholder="Ej: Inflamación tras ejercicio")
        
        # Uploader de fotos
        uploaded_photo = st.file_uploader(
            "Sube una foto",
            type=["jpg", "jpeg", "png"],
            key="foto_articulacion"
        )
        
        if uploaded_photo:
            st.image(uploaded_photo, caption=f"{articulacion} - {date.today()}", width=300)
            
            if st.button("💾 Guardar Foto", type="primary"):
                # Guardar archivo
                ruta_fotos = os.path.join("mobile_app", "fotos_pacientes", paciente["id"])
                os.makedirs(ruta_fotos, exist_ok=True)
                
                nombre_archivo = f"{date.today()}_{articulacion.replace(' ', '_')}_{uploaded_photo.name}"
                ruta_completa = os.path.join(ruta_fotos, nombre_archivo)
                
                with open(ruta_completa, "wb") as f:
                    f.write(uploaded_photo.getbuffer())
                
                # Guardar referencia en paciente
                from data_manager import guardar_paciente
                
                if "fotos_articulaciones" not in paciente:
                    paciente["fotos_articulaciones"] = []
                
                paciente["fotos_articulaciones"].append({
                    "fecha": date.today().strftime("%Y-%m-%d"),
                    "articulacion": articulacion,
                    "nota": nota_foto,
                    "archivo": nombre_archivo
                })
                
                guardar_paciente(paciente)
                st.success("✅ Foto guardada correctamente")
        
        # Mostrar fotos previas
        st.markdown("---")
        st.markdown("**📸 Fotos anteriores**")
        
        fotos_previas = paciente.get("fotos_articulaciones", [])
        if fotos_previas:
            # Agrupar por articulación
            from collections import defaultdict
            fotos_por_art = defaultdict(list)
            for foto in fotos_previas:
                fotos_por_art[foto["articulacion"]].append(foto)
            
            for art, fotos in fotos_por_art.items():
                with st.expander(f"📍 {art} ({len(fotos)} fotos)"):
                    for foto in sorted(fotos, key=lambda x: x["fecha"], reverse=True):
                        ruta_foto = os.path.join("mobile_app", "fotos_pacientes", paciente["id"], foto["archivo"])
                        if os.path.exists(ruta_foto):
                            col_img, col_info = st.columns([1, 2])
                            with col_img:
                                st.image(ruta_foto, width=150)
                            with col_info:
                                st.caption(f"📅 {foto['fecha']}")
                                if foto.get("nota"):
                                    st.caption(f"📝 {foto['nota']}")
                        else:
                            st.caption(f"📅 {foto['fecha']} - Archivo no encontrado")
        else:
            st.info("No has subido ninguna foto todavía.")
    
    # ==========================================================================
    # 💬 TAB 4: CHATBOT (Sin cambios)
    # ==========================================================================
    with tab_chat:
        st.markdown("##### 🤖 Asistente ReumaGPT")
        
        if "mensajes_paciente" not in st.session_state:
            st.session_state.mensajes_paciente = [
                {"role": "assistant", "content": f"Hola {paciente['nombre'].split()[0]}, soy tu asistente virtual."}
            ]

        for msg in st.session_state.mensajes_paciente:
            with st.chat_message(msg["role"]): st.write(msg["content"])

        if prompt := st.chat_input("Duda sobre tu tratamiento..."):
            st.session_state.mensajes_paciente.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Leyendo plan médico..."):
                    respuesta = responder_duda_paciente(prompt, historial, paciente["nombre"])
                    st.write(respuesta)
            st.session_state.mensajes_paciente.append({"role": "assistant", "content": respuesta})

    # ==========================================================================
    # 📄 TAB 5: INFORMES (Con el fix del botón)
    # ==========================================================================
    with tab_info:
        if not historial:
            st.warning("Sin informes.")
        else:
            for i, visita in enumerate(reversed(historial)):
                if isinstance(visita, dict):
                    f = visita.get("fecha", "S/F")
                    with st.expander(f"📄 Informe del {f}"):
                        st.write(visita.get('plan_tratamiento', '-'))
                        st.download_button("Descargar PDF", data="PDF", file_name=f"Inf_{f}.pdf", key=f"dl_{i}")