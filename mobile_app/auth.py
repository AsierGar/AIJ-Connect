"""
================================================================================
AUTH.PY - Sistema de Autenticación
================================================================================

Módulo que gestiona la autenticación de usuarios en AIJ-Connect.

FUNCIONALIDADES:
- Pantalla de login con logo y estilos personalizados
- Verificación de credenciales (usuario/contraseña)
- Gestión de sesión (login/logout)
- Almacenamiento de estado de autenticación en session_state

CREDENCIALES POR DEFECTO:
    Usuario: admin
    Contraseña: admin

NOTA: En producción, este sistema debería conectarse a una base de datos
real con contraseñas hasheadas. El sistema actual es solo para desarrollo.
================================================================================
"""

import streamlit as st
import os


def check_password():
    """
    Verifica si el usuario está autenticado correctamente.
    
    Si no hay sesión activa, muestra la pantalla de login.
    Si las credenciales son incorrectas, muestra error.
    
    Returns:
        bool: True si el usuario está autenticado, False en caso contrario
    
    FLUJO:
    1. Si no hay estado de autenticación -> mostrar login
    2. Si password_correct es False -> mostrar error
    3. Si password_correct es True -> permitir acceso
    """
    
    def password_entered():
        """
        Callback que se ejecuta cuando el usuario presiona 'Entrar'.
        
        Verifica las credenciales y actualiza el estado de sesión.
        Por seguridad, elimina la contraseña de session_state después de verificar.
        """
        if st.session_state["username"] == "admin" and st.session_state["password"] == "admin":
            st.session_state["password_correct"] = True
            # Limpiar credenciales de la sesión por seguridad
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # =========================================================================
    # CASO 1: Primera visita (no hay estado de autenticación)
    # =========================================================================
    if "password_correct" not in st.session_state:
        # Espaciado superior para centrar visualmente
        st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)
        
        # Layout de 3 columnas para centrar el formulario
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            # --- LOGO CENTRADO ---
            logo_path = os.path.join(os.path.dirname(__file__), "Logo.png")
            if os.path.exists(logo_path):
                st.image(logo_path, width=200, use_container_width=False)
            
            # --- TÍTULO Y SUBTÍTULO ---
            st.markdown("""
                <div style='text-align: center; margin-bottom: 30px;'>
                    <h2 style='color: #C41E3A; margin: 10px 0 5px 0;'>AIJ-Connect</h2>
                    <p style='color: #666; font-size: 0.9rem;'>Plataforma de Reumatología Pediátrica</p>
                </div>
            """, unsafe_allow_html=True)
            
            # --- FORMULARIO DE LOGIN ---
            with st.container(border=True):
                st.text_input("👤 Usuario", key="username", placeholder="Introduce tu usuario")
                st.text_input("🔒 Contraseña", type="password", key="password", placeholder="Introduce tu contraseña")
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.button("Entrar", on_click=password_entered, type="primary", use_container_width=True)
            
            # --- FOOTER ---
            st.markdown("""
                <div style='text-align: center; margin-top: 20px; color: #999; font-size: 0.8rem;'>
                    © 2025 AIJ-Connect | v1.0
                </div>
            """, unsafe_allow_html=True)
        return False
    
    # =========================================================================
    # CASO 2: Credenciales incorrectas
    # =========================================================================
    elif not st.session_state["password_correct"]:
        st.error("Usuario incorrecto")
        return False
    
    # =========================================================================
    # CASO 3: Usuario autenticado correctamente
    # =========================================================================
    return True


def cerrar_sesion():
    """
    Cierra la sesión del usuario actual.
    
    Elimina el estado de autenticación y recarga la página
    para mostrar la pantalla de login.
    """
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    st.rerun()
