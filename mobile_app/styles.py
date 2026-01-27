"""
🎨 Estilos personalizados para AIJ-Connect
Inyecta CSS para mejorar la apariencia de Streamlit
"""

import streamlit as st

def inject_custom_css():
    """Inyecta CSS personalizado en la app."""
    
    st.markdown("""
    <style>
    /* ============================================
       🎨 AIJ-CONNECT - ESTILOS PERSONALIZADOS
       Paleta: Rojo Granate + Grises elegantes
    ============================================ */
    
    /* --- VARIABLES CSS --- */
    :root {
        --primary: #C41E3A;
        --primary-dark: #9B1B30;
        --primary-light: #E8364F;
        --primary-soft: #FFF0F3;
        --accent: #FF6B6B;
        --success: #38A169;
        --warning: #ECC94B;
        --info: #4299E1;
        --text-dark: #2D3748;
        --text-muted: #718096;
        --bg-light: #FAFAFA;
        --bg-card: #FFFFFF;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
        --radius: 12px;
    }
    
    /* --- TIPOGRAFÍA MEJORADA --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Aplicar fuente solo a contenido de texto principal */
    .stMarkdown p, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6,
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stTextArea label, .stTextArea textarea,
    input, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600 !important;
        color: var(--text-dark) !important;
    }
    
    /* --- SIDEBAR ELEGANTE --- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFF5F5 0%, #FFFFFF 100%) !important;
        border-right: 1px solid rgba(196, 30, 58, 0.1) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        padding: 0 0.5rem;
    }
    
    /* Logo en sidebar */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        margin: 0 auto;
        display: block;
    }
    
    /* --- BOTONES MEJORADOS --- */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s ease !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Botón primario */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: white !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%) !important;
    }
    
    /* Botón secundario */
    .stButton > button[kind="secondary"] {
        background: white !important;
        border: 1.5px solid var(--primary) !important;
        color: var(--primary) !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: var(--primary-soft) !important;
    }
    
    /* --- INPUTS ESTILIZADOS --- */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        border-radius: 8px !important;
        border: 1.5px solid #E2E8F0 !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(196, 30, 58, 0.1) !important;
    }
    
    /* --- MÉTRICAS CON ESTILO --- */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        padding: 1rem 1.25rem !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-sm) !important;
        border-left: 4px solid var(--primary) !important;
    }
    
    [data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 700 !important;
    }
    
    /* --- TABS MEJORADOS --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background: transparent !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        background: #F7FAFC !important;
        border: none !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--primary) !important;
        border-bottom: 3px solid var(--primary) !important;
    }
    
    /* --- EXPANDERS ELEGANTES --- */
    [data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: var(--radius) !important;
    }
    
    [data-testid="stExpander"]:hover {
        border-color: var(--primary) !important;
    }
    
    /* Asegurar que los iconos de Streamlit se muestren correctamente */
    [data-testid="stExpander"] svg,
    [data-testid="stExpander"] [data-testid*="icon"] {
        font-family: inherit !important;
    }
    
    /* --- CONTENEDORES CON BORDE --- */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stVerticalBlockBorderWrapper"]) {
        border-radius: var(--radius) !important;
        border: 1px solid #E2E8F0 !important;
        padding: 1rem !important;
        background: var(--bg-card) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    /* --- ALERTAS PERSONALIZADAS --- */
    .stAlert {
        border-radius: var(--radius) !important;
        border: none !important;
    }
    
    /* Success */
    [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentSuccess"]) {
        background: linear-gradient(135deg, #F0FFF4 0%, #C6F6D5 100%) !important;
        border-left: 4px solid var(--success) !important;
    }
    
    /* Error/Warning */
    [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentError"]) {
        background: linear-gradient(135deg, #FFF5F5 0%, #FED7D7 100%) !important;
        border-left: 4px solid var(--primary) !important;
    }
    
    /* Info */
    [data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentInfo"]) {
        background: linear-gradient(135deg, #EBF8FF 0%, #BEE3F8 100%) !important;
        border-left: 4px solid var(--info) !important;
    }
    
    /* --- RADIO BUTTONS COMO PILLS --- */
    [data-testid="stRadio"] > div {
        gap: 0.5rem !important;
    }
    
    [data-testid="stRadio"] label {
        background: #F7FAFC !important;
        padding: 0.5rem 1rem !important;
        border-radius: 20px !important;
        border: 1.5px solid transparent !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    
    [data-testid="stRadio"] label:hover {
        background: var(--primary-soft) !important;
        border-color: var(--primary) !important;
    }
    
    [data-testid="stRadio"] label[data-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
    }
    
    /* --- SELECTBOX MEJORADO --- */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border-radius: 8px !important;
        border: 1.5px solid #E2E8F0 !important;
    }
    
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(196, 30, 58, 0.1) !important;
    }
    
    /* --- PROGRESS/SPINNER --- */
    .stSpinner > div {
        border-top-color: var(--primary) !important;
    }
    
    /* --- DIVIDERS --- */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, #E2E8F0, transparent) !important;
        margin: 1.5rem 0 !important;
    }
    
    /* --- DATAFRAMES/TABLAS --- */
    [data-testid="stDataFrame"] {
        border-radius: var(--radius) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    /* --- PILLS/TAGS --- */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background: var(--primary) !important;
        border-radius: 16px !important;
    }
    
    /* --- JSON VIEWER --- */
    [data-testid="stJson"] {
        background: #1a1a2e !important;
        border-radius: var(--radius) !important;
        padding: 1rem !important;
    }
    
    /* --- HEADER PRINCIPAL --- */
    h1:first-of-type {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* --- ANIMACIÓN SUTIL EN CARDS --- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* --- OCULTAR BRANDING STREAMLIT --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* --- ASEGURAR COMPONENTES EXTERNOS VISIBLES --- */
    iframe {
        display: block !important;
        visibility: visible !important;
    }
    
    [data-testid="stCustomComponentV1"] {
        display: block !important;
        visibility: visible !important;
        min-height: 600px !important;
    }
    
    /* --- SCROLLBAR PERSONALIZADA --- */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #F7FAFC;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #CBD5E0;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary);
    }
    
    </style>
    """, unsafe_allow_html=True)


def inject_custom_header():
    """Añade un header personalizado (opcional)."""
    st.markdown("""
    <style>
    .custom-header {
        background: linear-gradient(135deg, #C41E3A 0%, #9B1B30 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 0 0 20px 20px;
        margin: -1rem -1rem 1.5rem -1rem;
        box-shadow: 0 4px 15px rgba(196, 30, 58, 0.3);
    }
    .custom-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: white !important;
        -webkit-text-fill-color: white !important;
    }
    .custom-header p {
        margin: 0.25rem 0 0 0;
        opacity: 0.9;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

