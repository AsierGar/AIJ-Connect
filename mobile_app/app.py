"""
================================================================================
APP.PY - Punto de Entrada Principal de AIJ-Connect
================================================================================

Este es el archivo principal de la aplicación Streamlit. Gestiona:
- Configuración inicial de la página (título, favicon, layout)
- Sistema de autenticación (login/logout)
- Navegación entre diferentes vistas según el rol del usuario
- Enrutamiento a los diferentes módulos de la aplicación

ROLES DE USUARIO:
1. Reumatólogo: Acceso completo (dashboard, visitas, alta pacientes)
2. Paciente: Vista limitada (calendario, chatbot)

VISTAS DISPONIBLES:
- Vista Global: Dashboard con todos los pacientes
- Paciente: Ficha individual del paciente seleccionado
- Nueva Visita: Formulario para registrar consultas
- Nuevo Paciente: Alta de nuevos pacientes

USO:
    streamlit run mobile_app/app.py

ESTRUCTURA DE NAVEGACIÓN:
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR                           │  CONTENIDO PRINCIPAL       │
├─────────────────────────────────────┼───────────────────────────│
│  [Logo AIJ-Connect]                │                            │
│                                    │  Vista según selección:    │
│  Modo: 👨‍⚕️ Reumatólogo / 👶 Paciente │  - Dashboard Global       │
│                                    │  - Dashboard Paciente      │
│  Menú:                             │  - Nueva Visita            │
│  - 🌐 Vista Global                  │  - Alta Paciente          │
│  - 📂 Paciente                      │  - Portal Paciente        │
│  - ➕ Nuevo Paciente                │                            │
│                                    │                            │
│  [Cerrar Sesión]                   │                            │
└─────────────────────────────────────┴───────────────────────────┘
================================================================================
"""

import streamlit as st
import sys
import os

# Desactivar telemetría de CrewAI para evitar problemas de conexión
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import base64


def get_logo_base64():
    """
    Carga el logo y lo convierte a base64 para usar como favicon.
    
    Returns:
        str: Logo codificado en base64, o None si no existe
    """
    logo_path = os.path.join(os.path.dirname(__file__), "Logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# =============================================================================
# CONFIGURACIÓN DE PÁGINA (debe ser la primera llamada a Streamlit)
# =============================================================================
st.set_page_config(
    page_title="AIJ-Connect", 
    page_icon="mobile_app/Logo.png",
    layout="wide",                    # Usar todo el ancho disponible
    initial_sidebar_state="expanded"  # Sidebar abierto por defecto
)

# Añadir path para imports del backend de IA
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Inyectar estilos CSS personalizados
from styles import inject_custom_css
inject_custom_css()

# =============================================================================
# IMPORTS DE MÓDULOS INTERNOS
# =============================================================================
from auth import check_password, cerrar_sesion
from data_manager import cargar_pacientes
from ui_alta import render_alta_paciente
from ui_dashboard import render_dashboard, render_dashboard_global
from ui_visita import render_nueva_visita 

# Importar vista de paciente (intenta ambos nombres de archivo)
try:
    from ui_paciente import render_vista_paciente
except ImportError:
    from ui_patient import render_vista_paciente

# =============================================================================
# VERIFICACIÓN DE AUTENTICACIÓN
# =============================================================================
# Si el usuario no está logueado, mostrar pantalla de login y detener
if not check_password():
    st.stop()

# Inicializar paciente seleccionado en la sesión (compartido entre vistas)
if "paciente_seleccionado_global" not in st.session_state:
    st.session_state.paciente_seleccionado_global = None

# =============================================================================
# BARRA LATERAL (Navegación Global)
# =============================================================================
with st.sidebar:
    # --- LOGO ---
    ruta_logo = os.path.join(os.path.dirname(__file__), "Logo.png")
    if os.path.exists(ruta_logo):
        st.image(ruta_logo, width=220)
    else:
        # Fallback si no hay logo
        st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=50)
        st.title("AIJ-Connect")

    # --- SELECTOR DE ROL ---
    # Permite cambiar entre vista de médico y vista de paciente
    rol = st.radio("Modo de Vista:", ["👨‍⚕️ Reumatólogo", "👶 Paciente"], index=0)
    st.markdown("---")

    # --- MENÚ DE REUMATÓLOGO ---
    if rol == "👨‍⚕️ Reumatólogo":
        # Si hay una visita activa, bloquear el menú normal
        if st.session_state.get("modo_visita", False):
            st.info("📝 Visita en curso...")
            if st.button("Volver al Dashboard"):
                st.session_state.modo_visita = False
                st.rerun()
            modo = "VISITA_ACTIVA"
        else:
            # Determinar índice por defecto (ir a paciente si viene de Vista Global)
            default_idx = 0
            if st.session_state.pop("ir_a_paciente", False):
                default_idx = 1  # Índice de "📂 Paciente"
            
            modo = st.radio("Menú Médico", ["🌐 Vista Global", "📂 Paciente", "➕ Nuevo Paciente"], index=default_idx)
            
            # --- BUSCADOR DE PACIENTES ---
            # Solo visible cuando se selecciona modo "Paciente"
            if modo == "📂 Paciente":
                # Limpiar estado de alta si venimos de otra vista
                if 'nuevo_nhc' in st.session_state: 
                    del st.session_state['nuevo_nhc']
                
                # Cargar lista de pacientes para el selector
                db = cargar_pacientes()
                lista_display = [f"[{v.get('numero_historia')}] - {v['nombre']}" for k,v in db.items()]
                
                # Mantener la selección actual si existe
                idx_sel = 0
                if st.session_state.get("paciente_seleccionado_global"):
                    cur_nhc = st.session_state.paciente_seleccionado_global.get('numero_historia')
                    for i, item in enumerate(lista_display):
                        if cur_nhc in item:
                            idx_sel = i + 1
                            break
                
                # Selector de paciente
                sel = st.selectbox("Buscar Paciente:", [""] + lista_display, index=idx_sel)
                
                # Actualizar paciente seleccionado
                if sel: 
                    nhc = sel.split("]")[0].replace("[","")
                    for k,v in db.items(): 
                        if v.get("numero_historia") == nhc: 
                            st.session_state.paciente_seleccionado_global = v
                            break
                else:
                    st.session_state.paciente_seleccionado_global = None

    # --- MENÚ DE PACIENTE ---
    else:
        st.info("👁️ Estás viendo el portal tal como lo vería el paciente seleccionado.")
        modo = "VISTA_PACIENTE"

    # --- BOTÓN CERRAR SESIÓN ---
    st.markdown("---")
    st.button("Cerrar Sesión", on_click=cerrar_sesion, use_container_width=True)

# =============================================================================
# LÓGICA DE ENRUTAMIENTO (ROUTER PRINCIPAL)
# =============================================================================

# --- CASO 1: VISTA PACIENTE ---
if rol == "👶 Paciente":
    paciente = st.session_state.paciente_seleccionado_global
    
    if paciente:
        # Renderizar portal del paciente (Calendario + Chat)
        render_vista_paciente(paciente)
    else:
        # Aviso si no hay paciente seleccionado
        st.warning("⚠️ Para probar la vista de paciente, primero selecciona uno en el Dashboard de Reumatólogo.")
        c1, c2, c3 = st.columns([1,2,1])
        c2.image("https://cdn-icons-png.flaticon.com/512/10479/10479893.png", width=200, caption="Selecciona un paciente primero")


# --- CASO 2: VISTA REUMATÓLOGO ---
else:
    # A. VISITA EN CURSO (Prioridad máxima)
    if st.session_state.get("modo_visita", False) and st.session_state.get("paciente_visita"):
        render_nueva_visita(st.session_state.paciente_visita)

    # B. VISTA GLOBAL (Dashboard de todos los pacientes)
    elif modo == "🌐 Vista Global":
        db = cargar_pacientes()
        
        def seleccionar_paciente(pac):
            """Callback para seleccionar paciente desde el dashboard global."""
            st.session_state.paciente_seleccionado_global = pac
            st.session_state.ir_a_paciente = True
            st.rerun()
        
        render_dashboard_global(db, seleccionar_paciente_callback=seleccionar_paciente)
    
    # C. DASHBOARD INDIVIDUAL DE PACIENTE
    elif modo == "📂 Paciente":
        paciente = st.session_state.paciente_seleccionado_global
        
        if paciente:
            def ir_a_visita():
                """Callback para iniciar visita desde el dashboard."""
                st.session_state.paciente_visita = paciente
                st.session_state.modo_visita = True
                st.rerun()
                
            render_dashboard(paciente, ir_a_visita_callback=ir_a_visita)
        else:
            # Pantalla de aviso cuando no hay paciente seleccionado
            st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">📂 Dashboard de Paciente</h1>
                <p style="color: #718096; font-size: 1.1rem;">Seleccione un paciente para ver su ficha</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("👈 Seleccione un paciente en la barra lateral, o vaya a **Vista Global** para ver todos los pacientes.")

    # D. ALTA NUEVO PACIENTE
    elif modo == "➕ Nuevo Paciente":
        render_alta_paciente()
