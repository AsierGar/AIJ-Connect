"""
================================================================================
HOMUNCULO_VISITA.PY - Homúnculo Interactivo para Visitas Médicas
================================================================================

Este módulo implementa el componente interactivo del homúnculo que permite
a los médicos marcar articulaciones afectadas durante las visitas.

FUNCIONALIDAD:
- Muestra imagen del homúnculo (figura humana esquemática)
- Detecta clics del usuario usando streamlit-image-coordinates
- Identifica la articulación más cercana al clic
- Toggle: si ya está marcada, la quita; si no, la añade

COORDENADAS:
Las coordenadas están calibradas para una imagen de 400x600 píxeles.
Cada articulación tiene su posición (x, y) definida manualmente.

ARTICULACIONES SOPORTADAS (73 total):
- Cabeza/Cuello: ATM, Cervical, Esternoclavicular, Acromioclavicular
- Miembro Superior: Glenohumeral, Codo, Carpo
- Manos: MCF (1-5), IFP (2-5), IFD (1-5)
- Miembro Inferior: Cadera, Rodilla, Tobillo
- Pies: Subastragalina, Intertarsiana, MTF (1-5), IF (1-5)

USO:
    from homunculo_visita import renderizar_homunculo
    
    # En tu componente Streamlit:
    articulaciones = st.session_state.get("arts", set())
    articulaciones = renderizar_homunculo(articulaciones)
    st.session_state.arts = articulaciones
================================================================================
"""

import streamlit as st
import math
import os

# Configuración
IMG_PATH = os.path.join(os.path.dirname(__file__), "homunculo.png")
RADIO_CLIC = 12  # Radio de detección de clic en píxeles

# =============================================================================
# COORDENADAS DE ARTICULACIONES (calibradas para imagen 400x600)
# =============================================================================
COORDINADAS = {
    # --- CABEZA Y CUELLO ---
    "ATM Der.": (183, 58), "ATM Izq.": (226, 59),
    "Cervical": (203, 82),
    "Esternoclavicular Der.": (190, 106), "Esternoclavicular Izq.": (219, 105), 
    "Acromioclavicular Der.": (164, 92), "Acromioclavicular Izq.": (244, 92),

    # --- MIEMBRO SUPERIOR ---
    "Glenohumeral Der.": (145, 116), "Glenohumeral Izq.": (264, 112),
    "Codo Der.": (143, 191), "Codo Izq.": (265, 190),
    "Carpo Der.": (126, 265), "Carpo Izq.": (282, 264),
    
    # --- MANOS: MCF (Metacarpofalángicas) ---
    "Trapeciometacarpiana Der.": (136, 297), "Trapeciometacarpiana Izq.": (273, 293),
    "1ª MCF Der.": (133, 338), "1ª MCF Izq.": (277, 340),
    "2ª MCF Der.": (121, 323), "2ª MCF Izq.": (287, 324),
    "3ª MCF Der.": (105, 312), "3ª MCF Izq.": (304, 309),
    "4ª MCF Der.": (91, 296), "4ª MCF Izq.": (317, 295),
    "5ª MCF Der.": (78, 277), "5ª MCF Izq.": (331, 277),
    
    # --- MANOS: IFP (Interfalángicas Proximales) ---
    "2ª IFP Der.": (99, 351), "2ª IFP Izq.": (310, 352),
    "3ª IFP Der.": (330, 341), "3ª IFP Izq.": (340, 500), 
    "4ª IFP Der.": (67, 321), "4ª IFP Izq.": (344, 322),
    "5ª IFP Der.": (55, 296), "5ª IFP Izq.": (353, 297),
    
    # --- MANOS: IFD (Interfalángicas Distales) ---
    "1ª IFD Der.": (128, 363), "1ª IFD Izq.": (282, 363),
    "2ª IFD Der.": (87, 376), "2ª IFD Izq.": (322, 376),
    "3ª IFD Der.": (62, 363), "3ª IFD Izq.": (346, 362),
    "4ª IFD Der.": (45, 345), "4ª IFD Izq.": (366, 346),
    "5ª IFD Der.": (37, 315), "5ª IFD Izq.": (372, 316),

    # --- MIEMBRO INFERIOR ---
    "Cadera Der.": (171, 274), "Cadera Izq.": (235, 273),
    "Rodilla Der.": (171, 383), "Rodilla Izq.": (237, 378),
    "Tobillo Der.": (170, 468), "Tobillo Izq.": (239, 467),
    
    # --- PIES: TARSO ---
    "Subastragalina Der.": (176, 500), "Subastragalina Izq.": (233, 497),
    "Intertarsiana Der.": (132, 498), "Intertarsiana Izq.": (277, 498),
    
    # --- PIES: MTF (Metatarsofalángicas) ---
    "1ª MTF Der.": (156, 557), "1ª MTF Izq.": (252, 554),
    "2ª MTF Der.": (136, 557), "2ª MTF Izq.": (271, 557),
    "3ª MTF Der.": (117, 552), "3ª MTF Izq.": (292, 552),
    "4ª MTF Der.": (99, 545), "4ª MTF Izq.": (310, 543),
    "5ª MTF Der.": (78, 533), "5ª MTF Izq.": (330, 533),
    
    # --- PIES: IF (Interfalángicas del pie) ---
    "1ª IF Pie Der.": (156, 580), "1ª IF Pie Izq.": (254, 578),
    "2ª IF Pie Der.": (132, 581), "2ª IF Pie Izq.": (275, 579),
    "3ª IF Pie Der.": (111, 578), "3ª IF Pie Izq.": (299, 576),
    "4ª IF Pie Der.": (92, 567), "4ª IF Pie Izq.": (317, 566),
    "5ª IF Pie Der.": (66, 558), "5ª IF Pie Izq.": (343, 557),
}


def renderizar_homunculo(conjunto_seleccionadas, key_suffix="visita"):
    """
    Renderiza el homúnculo interactivo y gestiona la selección de articulaciones.
    
    Args:
        conjunto_seleccionadas: Set de nombres de articulaciones ya seleccionadas
        key_suffix: Sufijo para las keys de Streamlit (permite múltiples instancias)
        
    Returns:
        set: Conjunto actualizado de articulaciones seleccionadas
        
    FUNCIONAMIENTO:
    1. Muestra la imagen del homúnculo usando streamlit_image_coordinates
    2. Cuando el usuario hace clic, captura las coordenadas
    3. Calcula la distancia a todas las articulaciones conocidas
    4. Si el clic está dentro del radio de alguna, hace toggle (añadir/quitar)
    5. Devuelve el conjunto actualizado
    """
    # Importar la librería de coordenadas (puede no estar instalada)
    try:
        from streamlit_image_coordinates import streamlit_image_coordinates
    except ImportError:
        st.error("⚠️ Falta librería: pip install streamlit-image-coordinates")
        return conjunto_seleccionadas

    # Verificar que existe la imagen
    if not os.path.exists(IMG_PATH):
        st.error(f"⚠️ No encuentro la imagen en: {IMG_PATH}")
        return conjunto_seleccionadas

    # =========================================================================
    # PASO 1: MOSTRAR IMAGEN Y CAPTURAR CLIC
    # =========================================================================
    coords = streamlit_image_coordinates(
        IMG_PATH, 
        width=400,  # Ancho fijo para coincidir con coordenadas
        key=f"homunculo_widget_{key_suffix}"
    )

    # =========================================================================
    # PASO 2: GESTIÓN DE ESTADO PARA DETECTAR NUEVO CLIC
    # =========================================================================
    # Guardamos las últimas coordenadas para no procesar el mismo clic dos veces
    session_key_last = f"last_coords_{key_suffix}"
    if session_key_last not in st.session_state:
        st.session_state[session_key_last] = None

    # =========================================================================
    # PASO 3: PROCESAR CLIC (Solo si es nuevo)
    # =========================================================================
    if coords and coords != st.session_state[session_key_last]:
        st.session_state[session_key_last] = coords
        
        click_x = coords["x"]
        click_y = coords["y"]
        
        match_found = False

        # Buscar si el clic cae cerca de alguna articulación
        for nombre, (tx, ty) in COORDINADAS.items():
            # Calcular distancia euclidiana
            distancia = math.sqrt((click_x - tx)**2 + (click_y - ty)**2)
            
            if distancia <= RADIO_CLIC:
                # Toggle: si está, quitar; si no, añadir
                if nombre in conjunto_seleccionadas:
                    conjunto_seleccionadas.remove(nombre)
                else:
                    conjunto_seleccionadas.add(nombre)
                match_found = True
                st.rerun()  # Refrescar para mostrar cambio
                break
        
        # Avisar si el clic no coincidió con ninguna articulación
        if not match_found:
            st.toast("⚠️ Clicaste en vacío", icon="🤏")

    return conjunto_seleccionadas
