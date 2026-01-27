"""
================================================================================
UI_ALTA.PY - Formulario de Alta de Nuevos Pacientes
================================================================================

Este módulo implementa la interfaz para registrar nuevos pacientes en el
sistema AIJ-Connect.

SECCIONES DEL FORMULARIO:
1. Identificación: NHC (manual o aleatorio), Nombre
2. Datos Biométricos: Fecha nacimiento, Sexo, Peso, Talla, BSA
3. Contexto Clínico: Diagnóstico, Fecha inicio síntomas, Antecedentes uveítis
4. Mapa Articular: Homúnculo interactivo para marcar articulaciones afectadas
5. Perfil Inmunológico: FR, ACPA, HLA-B27, ANAs

DATOS GUARDADOS:
- Información demográfica del paciente
- Diagnóstico con marcadores positivos (ej: "AIJ poliarticular (FR+, ANA+)")
- Articulaciones afectadas al debut
- Riesgo de uveítis calculado automáticamente

FLUJO:
1. Usuario completa formulario
2. Click en "Guardar Paciente"
3. Se validan campos obligatorios (NHC, Nombre)
4. Se calcula diagnóstico final y riesgo de uveítis
5. Se guarda en pacientes.json
6. Se resetea el formulario para nuevo registro
================================================================================
"""

import streamlit as st
import math
import time
from datetime import date
from data_manager import guardar_paciente, cargar_pacientes, generar_nhc_random

# Intentar importar el componente del homúnculo
try:
    from homunculo_visita import renderizar_homunculo
    HOMUNCULO_OK = True
except ImportError:
    HOMUNCULO_OK = False


def render_alta_paciente():
    """
    Renderiza el formulario completo de alta de paciente.
    
    Gestiona:
    - Estado del formulario en session_state
    - Validación de campos obligatorios
    - Cálculo de BSA, edad, tiempo de evolución
    - Selección de articulaciones con homúnculo
    - Guardado del paciente y reset del formulario
    """
    
    # =========================================================================
    # LÓGICA DE RESET DEL FORMULARIO
    # =========================================================================
    # Cuando se guarda un paciente, se activa "reset_alta" para limpiar todo
    # Usamos sobrescritura de valores en lugar de 'del' para forzar limpieza
    if st.session_state.get("reset_alta", False):
        # Resetear todos los campos a sus valores por defecto
        st.session_state.nuevo_nhc = ""
        st.session_state.nuevo_nombre = ""
        st.session_state.fecha_nac = date.today()
        st.session_state.sexo = "Mujer"
        st.session_state.nuevo_peso = 20.0
        st.session_state.nueva_talla = 100.0
        st.session_state.diagnostico_tipo = "AIJ sistémica"
        st.session_state.fecha_sintomas = date.today()
        st.session_state.historia_uveitis = False
        st.session_state.art_afectadas = set()
        
        # Eliminar claves dinámicas (radios, pills) que se regeneran
        keys_dinamicas = [k for k in st.session_state.keys() if k.startswith("rad_") or k.startswith("pills_")]
        for k in keys_dinamicas:
            del st.session_state[k]

        st.session_state.reset_alta = False
        st.rerun()

    # Inicialización segura de variables de estado
    if 'nuevo_nhc' not in st.session_state: 
        st.session_state.nuevo_nhc = ""
    if 'art_afectadas' not in st.session_state: 
        st.session_state.art_afectadas = set()

    def set_random_nhc():
        """Callback para generar NHC aleatorio."""
        st.session_state.nuevo_nhc = generar_nhc_random()

    # =========================================================================
    # INTERFAZ DEL FORMULARIO
    # =========================================================================
    st.title("Alta Paciente")
    
    with st.container(border=True):
        # --- SECCIÓN 1: IDENTIFICACIÓN ---
        c1, c2, c3 = st.columns([2, 1, 5])
        c1.text_input("NHC", key="nuevo_nhc")
        c2.write("")  # Espaciador
        c2.button("🎲", on_click=set_random_nhc)  # Botón para NHC aleatorio
        new_nombre = c3.text_input("Nombre", key="nuevo_nombre")
        
        # --- SECCIÓN 2: DATOS BIOMÉTRICOS ---
        st.markdown("##### 📏 Datos Biométricos")
        c4, c5, c6, c7, c8 = st.columns(5)
        
        # Fecha de nacimiento y cálculo de edad
        f_nac = c4.date_input("Nacimiento", date.today(), key="fecha_nac")
        edad = date.today().year - f_nac.year
        c4.caption(f"Edad: {edad} años")
        
        sexo = c5.selectbox("Sexo", ["Mujer", "Hombre"], key="sexo")
        new_peso = c6.number_input("Peso (kg)", 0.0, 150.0, 20.0, key="nuevo_peso")
        new_talla = c7.number_input("Talla (cm)", 0.0, 220.0, 100.0, key="nueva_talla")
        
        # Cálculo de Superficie Corporal (BSA) - Fórmula de Mosteller
        bsa = math.sqrt((new_peso * new_talla) / 3600) if new_peso > 0 and new_talla > 0 else 0.0
        c8.metric("S. Corporal (BSA)", f"{bsa:.2f} m²")

        st.markdown("---")
        
        # --- SECCIÓN 3: CONTEXTO CLÍNICO ---
        st.markdown("##### 🩺 Contexto Clínico")
        cc1, cc2, cc3 = st.columns([2, 2, 2])
        
        # Selector de tipo de AIJ
        tipo = cc1.selectbox(
            "Diagnóstico", 
            ["AIJ sistémica", "AIJ oligoarticular", "AIJ poliarticular", 
             "Artritis psoriásica", "Entesitis", "Indiferenciada"],
            key="diagnostico_tipo"
        )
        
        # Fecha inicio síntomas y tiempo de evolución
        f_sintomas = cc2.date_input("Inicio de Síntomas", date.today(), key="fecha_sintomas")
        tiempo_evolucion = (date.today() - f_sintomas).days // 30
        cc2.caption(f"Evolución: {tiempo_evolucion} meses")
        
        # Antecedentes de uveítis (importante para riesgo)
        st.write("")
        historia_uveitis = cc3.toggle("⚠️ ¿Antecedentes de Uveítis?", key="historia_uveitis")
        
        st.markdown("---")
        
        # --- SECCIÓN 4: MAPA ARTICULAR (HOMÚNCULO) ---
        st.subheader("🦴 Mapa Articular")
        ch1, ch2 = st.columns([1, 1])
        
        with ch1:
            # Contenedor estilizado para el homúnculo
            st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-radius: 12px;
                    padding: 15px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    border: 1px solid #dee2e6;
                ">
                    <p style="text-align:center; color:#C41E3A; font-weight:600; margin-bottom:5px;">
                        Articulaciones al Debut
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.caption("👆 Clica para marcar articulaciones afectadas")
            
            # Renderizar homúnculo interactivo
            if HOMUNCULO_OK:
                st.session_state.art_afectadas = renderizar_homunculo(st.session_state.art_afectadas)
            else:
                st.error("Error cargando componente Homúnculo.")

        with ch2:
            # Panel de gestión de articulaciones seleccionadas
            st.caption("📋 Selecciona las que quieras borrar y pulsa el botón.")
            lista_actual = sorted(list(st.session_state.art_afectadas))
            
            # Pills para seleccionar articulaciones a borrar
            marcadas_para_borrar = st.pills(
                "Articulaciones Activas", 
                options=lista_actual, 
                selection_mode="multi", 
                default=[], 
                key=f"pills_gestion_{len(lista_actual)}"
            )
            
            if marcadas_para_borrar:
                if st.button(f"🗑️ Borrar {len(marcadas_para_borrar)} seleccionadas", type="secondary"):
                    st.session_state.art_afectadas = st.session_state.art_afectadas - set(marcadas_para_borrar)
                    st.rerun()
            elif not lista_actual:
                st.info("No hay articulaciones marcadas.")
            
            st.markdown("---")
            
            # --- SECCIÓN 5: PERFIL INMUNOLÓGICO ---
            st.subheader("🧬 Perfil Inmunológico")
            
            def fila_anticuerpo(label):
                """Renderiza una fila de anticuerpo con radio Negativo/Positivo."""
                c_l, c_r = st.columns([2, 2])
                with c_l: 
                    st.markdown(f"**{label}**")
                with c_r: 
                    return st.radio(
                        label, 
                        ["Negativo (-)", "Positivo (+)"], 
                        horizontal=True, 
                        label_visibility="collapsed", 
                        key=f"rad_{label}"
                    )

            # Marcadores inmunológicos
            val_fr = fila_anticuerpo("Factor Reumatoide (FR)")
            val_acpa = fila_anticuerpo("Anticuerpo Anticitrulinado (ACPA)")
            val_hla = fila_anticuerpo("HLA-B27")
            val_ana = fila_anticuerpo("ANAs (Antinucleares)")

        # =====================================================================
        # BOTÓN GUARDAR
        # =====================================================================
        st.markdown("###")
        if st.button("💾 Guardar Paciente", type="primary", use_container_width=True):
            # Validación de campos obligatorios
            if not st.session_state.nuevo_nhc: 
                st.error("Falta el Número de Historia (NHC).")
            elif not new_nombre:
                st.error("Falta el Nombre del paciente.")
            else:
                # Construir diagnóstico final con marcadores positivos
                pos = []
                if "Positivo" in val_fr: pos.append("FR+")
                if "Positivo" in val_acpa: pos.append("ACPA+")
                if "Positivo" in val_hla: pos.append("HLA-B27+")
                if "Positivo" in val_ana: pos.append("ANA+")
                diag_fin = f"{tipo} ({', '.join(pos)})" if pos else tipo
                
                # Calcular riesgo de uveítis
                # - Muy Alto: antecedentes previos
                # - Alto: ANAs positivos
                # - Bajo: sin factores de riesgo
                if historia_uveitis:
                    riesgo = "Muy Alto (Recurrente)"
                elif "Positivo" in val_ana:
                    riesgo = "Alto"
                else:
                    riesgo = "Bajo"

                # Construir objeto paciente
                pdata = {
                    "id": f"P_{len(cargar_pacientes())+1}", 
                    "numero_historia": st.session_state.nuevo_nhc,
                    "nombre": new_nombre, 
                    "fecha_nacimiento": str(f_nac), 
                    "sexo": sexo, 
                    "edad": edad, 
                    "peso_actual": new_peso, 
                    "talla": new_talla, 
                    "bsa": round(bsa, 2),
                    "diagnostico": diag_fin, 
                    "fecha_sintomas": str(f_sintomas), 
                    "historia_uveitis": historia_uveitis,
                    "articulaciones_afectadas": sorted(list(st.session_state.art_afectadas)),
                    "perfil_inmuno": {"fr": val_fr, "acpa": val_acpa, "hla": val_hla, "ana": val_ana},
                    "ana": val_ana, 
                    "fr": val_fr, 
                    "riesgo_uveitis": riesgo,
                    "historial_peso": {str(date.today()): new_peso}
                }
                
                # Guardar en base de datos
                guardar_paciente(pdata)
                st.success(f"✅ Paciente {new_nombre} creado correctamente.")
                
                # Activar reset y recargar
                st.session_state.reset_alta = True
                time.sleep(1.5)
                st.rerun()
