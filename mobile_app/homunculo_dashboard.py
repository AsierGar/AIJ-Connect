"""
================================================================================
HOMUNCULO_DASHBOARD.PY - Heatmap de Afectación Articular (Solo Lectura)
================================================================================

Este módulo genera un heatmap visual del homúnculo mostrando la frecuencia
de afectación de cada articulación a lo largo del historial del paciente.

DIFERENCIA CON homunculo_visita.py:
- Este es SOLO LECTURA (no interactivo)
- Usa PIL para pintar círculos de colores sobre la imagen
- Muestra frecuencias históricas, no selección actual

PALETA DE COLORES (SEMÁFORO):
- Amarillo: 1 vez afectada
- Naranja: 2-3 veces afectada
- Rojo: 4+ veces afectada

USO:
    from homunculo_dashboard import renderizar_heatmap_dashboard
    
    # Diccionario con frecuencias: {"Rodilla Der.": 3, "Tobillo Izq.": 1, ...}
    frecuencias = calcular_frecuencias(historial)
    renderizar_heatmap_dashboard(frecuencias)
================================================================================
"""

import streamlit as st
from PIL import Image, ImageDraw
import os

# =============================================================================
# COORDENADAS DE ARTICULACIONES (calibradas para imagen 400x600)
# =============================================================================
# NOTA: Estas coordenadas son ligeramente diferentes a homunculo_visita.py
# porque fueron calibradas independientemente. En una refactorización futura
# se podrían unificar en un archivo compartido.
COORDENADAS_ARTICULACIONES = {
    # --- CABEZA Y CUELLO ---
    "ATM Der.": (182, 58),
    "ATM Izq.": (225, 58),
    "Cervical": (204, 80),
    "Esternoclavicular Der.": (191, 103),
    "Esternoclavicular Izq.": (218, 104),
    "Acromioclavicular Der.": (165, 90),
    "Acromioclavicular Izq.": (243, 91),
    
    # --- MIEMBRO SUPERIOR ---
    "Glenohumeral Der.": (145, 110),
    "Glenohumeral Izq.": (263, 110),
    "Codo Der.": (144, 187),
    "Codo Izq.": (265, 187),
    "Carpo Der.": (125, 261),
    "Carpo Izq.": (282, 261),
    
    # --- MANOS ---
    "Trapeciometacarpiana Der.": (134, 291),
    "Trapeciometacarpiana Izq.": (273, 292),
    "1ª MCF Der.": (133, 335),
    "1ª MCF Izq.": (275, 335),
    "2ª MCF Der.": (120, 320),
    "2ª MCF Izq.": (288, 320),
    "3ª MCF Der.": (105, 306),
    "3ª MCF Izq.": (303, 306),
    "4ª MCF Der.": (91, 292),
    "4ª MCF Izq.": (317, 291),
    "5ª MCF Der.": (78, 275),
    "5ª MCF Izq.": (330, 275),
    "2ª IFP Der.": (100, 347),
    "2ª IFP Izq.": (308, 347),
    "3ª IFP Der.": (81, 336),
    "3ª IFP Izq.": (328, 336),
    "4ª IFP Der.": (66, 318),
    "4ª IFP Izq.": (343, 318),
    "5ª IFP Der.": (55, 295),
    "5ª IFP Izq.": (353, 294),
    "1ª IFD Der.": (126, 358),
    "1ª IFD Izq.": (282, 358),
    "2ª IFD Der.": (87, 372),
    "2ª IFD Izq.": (322, 372),
    "3ª IFD Der.": (63, 360),
    "3ª IFD Izq.": (345, 359),
    "4ª IFD Der.": (44, 342),
    "4ª IFD Izq.": (365, 341),
    "5ª IFD Der.": (38, 313),
    "5ª IFD Izq.": (370, 313),
    
    # --- MIEMBRO INFERIOR ---
    "Cadera Der.": (171, 272),
    "Cadera Izq.": (237, 272),
    "Rodilla Der.": (172, 375),
    "Rodilla Izq.": (237, 375),
    "Tobillo Der.": (171, 464),
    "Tobillo Izq.": (240, 463),
    
    # --- PIES ---
    "Subastragalina Der.": (176, 493),
    "Subastragalina Izq.": (233, 492),
    "Intertarsiana Der.": (133, 493),
    "Intertarsiana Izq.": (277, 491),
    "1ª MTF Der.": (156, 551),
    "1ª MTF Izq.": (252, 549),
    "2ª MTF Der.": (137, 551),
    "2ª MTF Izq.": (272, 550),
    "3ª MTF Der.": (117, 548),
    "3ª MTF Izq.": (292, 546),
    "4ª MTF Der.": (99, 539),
    "4ª MTF Izq.": (310, 537),
    "5ª MTF Der.": (78, 528),
    "5ª MTF Izq.": (331, 527),
    "1ª IF Pie Der.": (156, 574),
    "1ª IF Pie Izq.": (253, 572),
    "2ª IF Pie Der.": (133, 575),
    "2ª IF Pie Izq.": (276, 573),
    "3ª IF Pie Der.": (111, 573),
    "3ª IF Pie Izq.": (298, 571),
    "4ª IF Pie Der.": (91, 563),
    "4ª IF Pie Izq.": (317, 560),
    "5ª IF Pie Der.": (67, 552),
    "5ª IF Pie Izq.": (342, 551),
}

# =============================================================================
# PALETA DE COLORES SEMÁFORO (RGBA con transparencia)
# =============================================================================
COLOR_BAJO = (255, 215, 0, 180)     # Amarillo Oro (1 brote)
COLOR_MEDIO = (255, 140, 0, 200)    # Naranja Intenso (2-3 brotes)
COLOR_ALTO = (220, 20, 60, 230)     # Rojo Carmesí (4+ brotes)


def _cargar_imagen_base():
    """
    Carga la imagen base del homúnculo.
    
    Returns:
        PIL.Image: Imagen RGBA de 400x600 píxeles
    """
    ruta_img = os.path.join(os.path.dirname(__file__), "homunculo.png")
    W, H = 400, 600  # Tamaño fijo para coincidir con coordenadas
    
    if not os.path.exists(ruta_img):
        # Si no existe la imagen, crear una vacía
        return Image.new('RGBA', (W, H), color=(240, 242, 246, 255))
    
    return Image.open(ruta_img).convert("RGBA").resize((W, H))


def renderizar_heatmap_dashboard(frecuencias_dict):
    """
    Genera y muestra el heatmap de afectación articular.
    
    Args:
        frecuencias_dict: Diccionario {nombre_articulacion: num_veces_afectada}
                         Ej: {"Rodilla Der.": 3, "Tobillo Izq.": 1}
    
    PROCESO:
    1. Carga la imagen base del homúnculo (400x600)
    2. Crea una capa transparente para los círculos
    3. Dibuja círculos de colores según la frecuencia
    4. Fusiona las capas
    5. Muestra la imagen a 250px (reducida para el dashboard)
    6. Añade leyenda de colores
    """
    # =========================================================================
    # PASO 1: CARGAR IMAGEN BASE
    # =========================================================================
    base_img = _cargar_imagen_base()
    
    # =========================================================================
    # PASO 2: CREAR CAPA TRANSPARENTE PARA DIBUJAR
    # =========================================================================
    overlay = Image.new('RGBA', base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # =========================================================================
    # PASO 3: DIBUJAR CÍRCULOS SEGÚN FRECUENCIA
    # =========================================================================
    for nombre, (cx, cy) in COORDENADAS_ARTICULACIONES.items():
        count = frecuencias_dict.get(nombre, 0)
        
        if count > 0:
            # Determinar color según frecuencia
            if count == 1:
                color = COLOR_BAJO
                outline = (200, 180, 0, 150)
            elif 2 <= count <= 3:
                color = COLOR_MEDIO
                outline = (200, 100, 0, 180)
            else:  # 4+
                color = COLOR_ALTO
                outline = (150, 0, 0, 220)

            # Dibujar círculo
            radius = 10
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius), 
                fill=color, 
                outline=outline
            )

    # =========================================================================
    # PASO 4: FUSIONAR CAPAS
    # =========================================================================
    comp = Image.alpha_composite(base_img, overlay)
    
    # =========================================================================
    # PASO 5: MOSTRAR IMAGEN
    # =========================================================================
    # Mostramos a 250px aunque la imagen es de 400px
    # Esto mantiene los puntos en posición correcta pero más compacto
    st.image(comp, caption="Patrón de Afectación Histórico", width=250)
    
    # =========================================================================
    # PASO 6: LEYENDA DE COLORES
    # =========================================================================
    st.markdown(
        """
        <div style="display: flex; justify-content: center; gap: 12px; font-size: 0.7em; color: gray; margin-top: -10px;">
            <div style="display:flex; align-items:center; gap:4px;"><div style='width:8px; height:8px; background-color:#FFD700; border-radius:50%;'></div> 1 vez</div>
            <div style="display:flex; align-items:center; gap:4px;"><div style='width:8px; height:8px; background-color:#FF8C00; border-radius:50%;'></div> 2-3 veces</div>
            <div style="display:flex; align-items:center; gap:4px;"><div style='width:8px; height:8px; background-color:#DC143C; border-radius:50%;'></div> 4+ veces</div>
        </div>
        """, unsafe_allow_html=True
    )
