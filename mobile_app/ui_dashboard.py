"""
================================================================================
UI_DASHBOARD.PY - Dashboard Clínico del Paciente
================================================================================

Este módulo implementa el dashboard principal para visualizar la información
clínica de un paciente individual y el dashboard global de todos los pacientes.

FUNCIONALIDADES PRINCIPALES:

1. DASHBOARD INDIVIDUAL (render_dashboard):
   - Métricas principales: JADAS, articulaciones activas, EVA
   - Gráficos de evolución temporal (JADAS, peso, tratamientos)
   - Heatmap de afectación articular histórica
   - Tabla de visitas con detalles
   - Generación de informes PDF
   - Gestión de fotos clínicas
   - Edición de datos del paciente

2. DASHBOARD GLOBAL (render_dashboard_global):
   - Tabla de todos los pacientes con métricas resumen
   - Gráficos comparativos poblacionales
   - Filtros por diagnóstico, estado, riesgo

MÉTRICAS CALCULADAS:
- JADAS-27/71: Índice de actividad de la enfermedad
- EVA médico/paciente: Escala visual analógica
- VSG: Velocidad de sedimentación
- Tendencias de peso vs percentiles OMS

DEPENDENCIAS EXTERNAS:
- Altair: Gráficos interactivos
- ReportLab: Generación de PDFs
- PIL: Procesamiento de imágenes
================================================================================
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
import time
import math
import io
import numpy as np
from datetime import datetime, date, timedelta
from data_manager import guardar_historial, cargar_historial_medico, guardar_paciente, borrar_paciente_db

# ==============================================================================
# 📈 CURVAS DE CRECIMIENTO OMS (Percentiles)
# ==============================================================================
# Datos simplificados de percentiles OMS para niños/niñas de 2-18 años
# Formato: {edad: {sexo: {percentil: valor}}}

# PESO (kg) - Percentiles P3, P15, P50, P85, P97
PESO_OMS = {
    "M": {  # Masculino
        2: {"P3": 10.5, "P15": 11.5, "P50": 12.5, "P85": 14.0, "P97": 15.5},
        3: {"P3": 12.0, "P15": 13.2, "P50": 14.5, "P85": 16.5, "P97": 18.5},
        4: {"P3": 13.5, "P15": 15.0, "P50": 16.5, "P85": 19.0, "P97": 21.5},
        5: {"P3": 15.0, "P15": 16.8, "P50": 18.5, "P85": 21.5, "P97": 25.0},
        6: {"P3": 16.5, "P15": 18.5, "P50": 20.5, "P85": 24.5, "P97": 29.0},
        7: {"P3": 18.0, "P15": 20.5, "P50": 23.0, "P85": 28.0, "P97": 33.5},
        8: {"P3": 20.0, "P15": 22.5, "P50": 25.5, "P85": 31.5, "P97": 38.5},
        9: {"P3": 22.0, "P15": 25.0, "P50": 28.5, "P85": 35.5, "P97": 44.0},
        10: {"P3": 24.0, "P15": 27.5, "P50": 32.0, "P85": 40.0, "P97": 50.0},
        11: {"P3": 26.5, "P15": 30.5, "P50": 35.5, "P85": 45.0, "P97": 56.5},
        12: {"P3": 29.5, "P15": 34.0, "P50": 40.0, "P85": 50.5, "P97": 63.0},
        13: {"P3": 33.0, "P15": 38.5, "P50": 45.5, "P85": 56.5, "P97": 69.5},
        14: {"P3": 38.0, "P15": 44.0, "P50": 51.5, "P85": 62.5, "P97": 75.0},
        15: {"P3": 43.5, "P15": 50.0, "P50": 57.5, "P85": 68.0, "P97": 80.0},
        16: {"P3": 48.5, "P15": 55.0, "P50": 62.5, "P85": 73.0, "P97": 84.5},
        17: {"P3": 52.5, "P15": 59.0, "P50": 66.5, "P85": 77.0, "P97": 88.0},
        18: {"P3": 55.0, "P15": 62.0, "P50": 69.5, "P85": 80.0, "P97": 91.0},
    },
    "F": {  # Femenino
        2: {"P3": 10.0, "P15": 11.0, "P50": 12.0, "P85": 13.5, "P97": 15.0},
        3: {"P3": 11.5, "P15": 12.8, "P50": 14.0, "P85": 16.0, "P97": 18.0},
        4: {"P3": 13.0, "P15": 14.5, "P50": 16.0, "P85": 18.5, "P97": 21.0},
        5: {"P3": 14.5, "P15": 16.2, "P50": 18.0, "P85": 21.0, "P97": 24.5},
        6: {"P3": 16.0, "P15": 18.0, "P50": 20.0, "P85": 24.0, "P97": 28.5},
        7: {"P3": 17.5, "P15": 20.0, "P50": 22.5, "P85": 27.5, "P97": 33.0},
        8: {"P3": 19.5, "P15": 22.5, "P50": 25.5, "P85": 31.5, "P97": 38.5},
        9: {"P3": 22.0, "P15": 25.5, "P50": 29.0, "P85": 36.0, "P97": 44.5},
        10: {"P3": 24.5, "P15": 28.5, "P50": 33.0, "P85": 41.5, "P97": 51.5},
        11: {"P3": 27.5, "P15": 32.0, "P50": 37.5, "P85": 47.5, "P97": 58.5},
        12: {"P3": 31.0, "P15": 36.0, "P50": 42.5, "P85": 53.0, "P97": 64.5},
        13: {"P3": 35.0, "P15": 40.5, "P50": 47.5, "P85": 57.5, "P97": 69.0},
        14: {"P3": 39.0, "P15": 44.5, "P50": 51.5, "P85": 61.0, "P97": 72.5},
        15: {"P3": 42.0, "P15": 47.5, "P50": 54.5, "P85": 63.5, "P97": 75.0},
        16: {"P3": 44.0, "P15": 49.5, "P50": 56.5, "P85": 65.5, "P97": 77.0},
        17: {"P3": 45.5, "P15": 51.0, "P50": 58.0, "P85": 67.0, "P97": 78.5},
        18: {"P3": 46.5, "P15": 52.0, "P50": 59.0, "P85": 68.0, "P97": 79.5},
    }
}

# TALLA (cm) - Percentiles P3, P15, P50, P85, P97
TALLA_OMS = {
    "M": {  # Masculino
        2: {"P3": 82, "P15": 85, "P50": 88, "P85": 91, "P97": 94},
        3: {"P3": 90, "P15": 93, "P50": 96, "P85": 100, "P97": 103},
        4: {"P3": 96, "P15": 100, "P50": 103, "P85": 107, "P97": 111},
        5: {"P3": 102, "P15": 106, "P50": 110, "P85": 114, "P97": 118},
        6: {"P3": 108, "P15": 112, "P50": 116, "P85": 121, "P97": 125},
        7: {"P3": 113, "P15": 117, "P50": 122, "P85": 127, "P97": 132},
        8: {"P3": 118, "P15": 123, "P50": 128, "P85": 133, "P97": 138},
        9: {"P3": 123, "P15": 128, "P50": 133, "P85": 139, "P97": 144},
        10: {"P3": 127, "P15": 133, "P50": 138, "P85": 144, "P97": 150},
        11: {"P3": 132, "P15": 138, "P50": 143, "P85": 150, "P97": 156},
        12: {"P3": 137, "P15": 143, "P50": 149, "P85": 156, "P97": 163},
        13: {"P3": 142, "P15": 149, "P50": 156, "P85": 163, "P97": 170},
        14: {"P3": 149, "P15": 156, "P50": 163, "P85": 171, "P97": 178},
        15: {"P3": 155, "P15": 162, "P50": 170, "P85": 177, "P97": 184},
        16: {"P3": 160, "P15": 167, "P50": 174, "P85": 181, "P97": 187},
        17: {"P3": 163, "P15": 170, "P50": 176, "P85": 183, "P97": 189},
        18: {"P3": 165, "P15": 171, "P50": 177, "P85": 184, "P97": 190},
    },
    "F": {  # Femenino
        2: {"P3": 80, "P15": 83, "P50": 86, "P85": 89, "P97": 92},
        3: {"P3": 88, "P15": 91, "P50": 95, "P85": 98, "P97": 102},
        4: {"P3": 95, "P15": 98, "P50": 102, "P85": 106, "P97": 110},
        5: {"P3": 101, "P15": 105, "P50": 109, "P85": 113, "P97": 117},
        6: {"P3": 107, "P15": 111, "P50": 115, "P85": 120, "P97": 124},
        7: {"P3": 112, "P15": 117, "P50": 121, "P85": 126, "P97": 131},
        8: {"P3": 117, "P15": 122, "P50": 127, "P85": 132, "P97": 138},
        9: {"P3": 122, "P15": 127, "P50": 133, "P85": 139, "P97": 145},
        10: {"P3": 127, "P15": 133, "P50": 138, "P85": 145, "P97": 151},
        11: {"P3": 132, "P15": 139, "P50": 145, "P85": 152, "P97": 158},
        12: {"P3": 139, "P15": 145, "P50": 152, "P85": 158, "P97": 164},
        13: {"P3": 145, "P15": 151, "P50": 157, "P85": 163, "P97": 168},
        14: {"P3": 149, "P15": 155, "P50": 160, "P85": 166, "P97": 171},
        15: {"P3": 151, "P15": 157, "P50": 162, "P85": 167, "P97": 172},
        16: {"P3": 152, "P15": 158, "P50": 163, "P85": 168, "P97": 173},
        17: {"P3": 153, "P15": 158, "P50": 163, "P85": 168, "P97": 173},
        18: {"P3": 153, "P15": 158, "P50": 163, "P85": 169, "P97": 174},
    }
}

def calcular_percentil(valor, edad, sexo, tipo="peso"):
    """Calcula en qué percentil se encuentra un valor dado."""
    datos = PESO_OMS if tipo == "peso" else TALLA_OMS
    sexo_key = "M" if sexo and sexo.lower() in ["m", "masculino", "hombre", "niño", "varón"] else "F"
    
    edad_int = max(2, min(18, int(edad)))
    if edad_int not in datos[sexo_key]:
        return None, "N/A"
    
    percentiles = datos[sexo_key][edad_int]
    
    if valor <= percentiles["P3"]:
        return 3, "< P3 ⚠️"
    elif valor <= percentiles["P15"]:
        return 10, "P3-P15"
    elif valor <= percentiles["P50"]:
        return 35, "P15-P50"
    elif valor <= percentiles["P85"]:
        return 65, "P50-P85"
    elif valor <= percentiles["P97"]:
        return 90, "P85-P97"
    else:
        return 97, "> P97"

def generar_curvas_percentiles(sexo, tipo="peso", edad_min=2, edad_max=18):
    """Genera DataFrames con las curvas de percentiles OMS."""
    datos = PESO_OMS if tipo == "peso" else TALLA_OMS
    sexo_key = "M" if sexo and sexo.lower() in ["m", "masculino", "hombre", "niño", "varón"] else "F"
    
    filas = []
    for edad in range(edad_min, edad_max + 1):
        if edad in datos[sexo_key]:
            for p_name, p_val in datos[sexo_key][edad].items():
                filas.append({"Edad": edad, "Percentil": p_name, "Valor": p_val})
    
    return pd.DataFrame(filas)

# Para exportar PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False

# Intentamos importar la IA (opcional)
try:
    from ai_backend.agents.tripulacion import ejecutar_validacion_medica
    IA_DISPONIBLE = True
except ImportError:
    IA_DISPONIBLE = False

# Intentamos importar el Heatmap del Dashboard (el archivo estático)
try:
    from homunculo_dashboard import renderizar_heatmap_dashboard
    HEATMAP_OK = True
except ImportError:
    HEATMAP_OK = False

# ==============================================================================
# 🚨 SISTEMA DE ALERTAS AUTOMÁTICAS
# ==============================================================================
def generar_id_alerta(tipo, fecha_referencia=None):
    """Genera un ID único para cada alerta basado en tipo y mes."""
    mes_actual = date.today().strftime("%Y-%m")
    return f"{tipo}_{mes_actual}"

def generar_alertas(paciente, historial):
    """Genera alertas clínicas basadas en el perfil del paciente y su historial."""
    alertas = []
    hoy = date.today()
    alertas_resueltas = paciente.get("alertas_resueltas", {})
    
    # --- 1. ALERTA OFTALMOLÓGICA (ANA+ y oligoarticular) ---
    perfil = paciente.get("perfil_inmuno", {})
    ana_positivo = "Positivo" in perfil.get("ana", "") or "+" in paciente.get("ana", "")
    es_oligoarticular = "oligoarticular" in paciente.get("diagnostico", "").lower()
    historia_uveitis = paciente.get("historia_uveitis", False)
    
    if ana_positivo or es_oligoarticular or historia_uveitis:
        # Buscar última revisión oftalmológica en historial
        ultima_oftalmo = None
        for visita in reversed(historial):
            if isinstance(visita, dict):
                texto = str(visita.get("pruebas", "")) + str(visita.get("plan_tratamiento", ""))
                if any(x in texto.lower() for x in ["lámpara", "lampara", "hendidura", "oftalm", "uveitis", "uveítis"]):
                    try:
                        ultima_oftalmo = datetime.strptime(visita.get("fecha", ""), "%Y-%m-%d").date()
                        break
                    except:
                        pass
        
        meses_desde_revision = 999
        if ultima_oftalmo:
            meses_desde_revision = (hoy - ultima_oftalmo).days // 30
        
        # Frecuencia recomendada: 3 meses si ANA+ y <7 años, 6 meses resto
        edad = paciente.get("edad", 10)
        frecuencia_meses = 3 if (ana_positivo and edad < 7) else 6
        
        if meses_desde_revision >= frecuencia_meses:
            alerta_id = generar_id_alerta("oftalmologia")
            # Solo mostrar si no está resuelta este mes
            if alerta_id not in alertas_resueltas:
                urgencia = "alta" if historia_uveitis else "media"
                texto_alerta = f"👁️ Revisión oftalmológica pendiente"
                if ultima_oftalmo:
                    texto_alerta += f" (última: hace {meses_desde_revision} meses)"
                else:
                    texto_alerta += " (sin registro previo)"
                alertas.append({"id": alerta_id, "tipo": "oftalmologia", "texto": texto_alerta, "urgencia": urgencia})
    
    # --- 2. ALERTA ANALÍTICA (si lleva MTX/biológico) ---
    ultimo_tratamiento = ""
    ultima_analitica = None
    
    for visita in reversed(historial):
        if isinstance(visita, dict):
            plan = str(visita.get("plan_tratamiento", "")).lower()
            if any(x in plan for x in ["metotrexato", "metotrexate", "mtx", "adalimumab", "etanercept", "tocilizumab", "humira"]):
                ultimo_tratamiento = plan
                break
    
    lleva_mtx = any(x in ultimo_tratamiento for x in ["metotrexato", "metotrexate", "mtx"])
    lleva_biologico = any(x in ultimo_tratamiento for x in ["adalimumab", "etanercept", "tocilizumab", "humira", "biológico"])
    
    if lleva_mtx or lleva_biologico:
        # Buscar última analítica con transaminasas
        for visita in reversed(historial):
            if isinstance(visita, dict):
                analitica = visita.get("analitica", {}) or visita.get("exploracion", {}).get("analitica", {})
                if analitica.get("ast") or analitica.get("alt") or analitica.get("hb"):
                    try:
                        ultima_analitica = datetime.strptime(visita.get("fecha", ""), "%Y-%m-%d").date()
                        break
                    except:
                        pass
        
        semanas_desde_analitica = 999
        if ultima_analitica:
            semanas_desde_analitica = (hoy - ultima_analitica).days // 7
        
        # MTX: cada 8-12 semanas (usamos 10 como umbral)
        umbral_semanas = 10 if lleva_mtx else 12
        
        if semanas_desde_analitica >= umbral_semanas:
            alerta_id = generar_id_alerta("analitica")
            # Solo mostrar si no está resuelta este mes
            if alerta_id not in alertas_resueltas:
                med_nombre = "MTX" if lleva_mtx else "Biológico"
                texto_alerta = f"🧪 Analítica de seguridad pendiente ({med_nombre})"
                if ultima_analitica:
                    texto_alerta += f" - última: hace {semanas_desde_analitica} semanas"
                alertas.append({"id": alerta_id, "tipo": "analitica", "texto": texto_alerta, "urgencia": "media"})
    
    # --- 3. ALERTA PACIENTE PERDIDO (>6 meses sin visita) ---
    if historial:
        ultima_visita = None
        for visita in reversed(historial):
            if isinstance(visita, dict) and visita.get("fecha"):
                try:
                    ultima_visita = datetime.strptime(visita.get("fecha"), "%Y-%m-%d").date()
                    break
                except:
                    pass
        
        if ultima_visita:
            meses_sin_visita = (hoy - ultima_visita).days // 30
            if meses_sin_visita >= 6:
                alerta_id = generar_id_alerta("perdido")
                if alerta_id not in alertas_resueltas:
                    alertas.append({
                        "id": alerta_id,
                        "tipo": "perdido",
                        "texto": f"📅 Paciente sin visita desde hace {meses_sin_visita} meses",
                        "urgencia": "alta" if meses_sin_visita >= 12 else "media"
                    })
    
    return alertas

def marcar_alerta_resuelta(paciente, alerta_id):
    """Marca una alerta como resuelta para este mes."""
    if "alertas_resueltas" not in paciente:
        paciente["alertas_resueltas"] = {}
    paciente["alertas_resueltas"][alerta_id] = date.today().strftime("%Y-%m-%d")
    guardar_paciente(paciente)
    return True

# ==============================================================================
# 📊 CÁLCULO DE JADAS (Juvenile Arthritis Disease Activity Score)
# ==============================================================================
def calcular_jadas(nad, eva_medico, eva_paciente, vsg=None, pcr=None):
    """
    Calcula el JADAS-27.
    JADAS-27 = NAD (0-27) + EVA médico (0-10) + EVA paciente (0-10) + marcador normalizado (0-10)
    
    El marcador inflamatorio (VSG o PCR) se normaliza a escala 0-10:
    - VSG: (VSG - 20) / 10, limitado a 0-10
    - PCR: si no hay VSG, se puede usar PCR con conversión aproximada
    """
    # NAD limitado a 27 (para JADAS-27)
    nad_score = min(float(nad or 0), 27)
    
    # EVAs en escala 0-10
    eva_med_score = min(max(float(eva_medico or 0), 0), 10)
    eva_pac_score = min(max(float(eva_paciente or 0), 0), 10)
    
    # Marcador inflamatorio normalizado
    marcador_score = 0
    if vsg is not None and vsg > 0:
        # Fórmula estándar: (VSG - 20) / 10, limitado entre 0 y 10
        marcador_score = max(0, min(10, (float(vsg) - 20) / 10))
    elif pcr is not None and pcr > 0:
        # Aproximación para PCR: PCR / 1 (asumiendo PCR en mg/L, normal <5)
        marcador_score = max(0, min(10, float(pcr) / 1))
    
    jadas = nad_score + eva_med_score + eva_pac_score + marcador_score
    
    return {
        "total": round(jadas, 1),
        "nad": nad_score,
        "eva_medico": eva_med_score,
        "eva_paciente": eva_pac_score,
        "marcador": round(marcador_score, 1),
        "interpretacion": interpretar_jadas(jadas)
    }

def interpretar_jadas(jadas):
    """Interpreta el score JADAS-27."""
    if jadas <= 1:
        return ("Remisión", "🟢")
    elif jadas <= 3.8:
        return ("Actividad baja", "🟡")
    elif jadas <= 10.5:
        return ("Actividad moderada", "🟠")
    else:
        return ("Actividad alta", "🔴")

# ==============================================================================
# 📄 GENERADOR DE INFORME PDF
# ==============================================================================
def generar_pdf_informe(paciente, historial, visita_seleccionada=None):
    """Genera un PDF con el informe clínico del paciente."""
    if not PDF_DISPONIBLE:
        return None
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=16, spaceAfter=20, alignment=1, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Subtitulo', fontSize=12, spaceAfter=10, fontName='Helvetica-Bold', textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='Normal2', fontSize=10, spaceAfter=6))
    
    elementos = []
    
    # Título
    elementos.append(Paragraph("INFORME CLÍNICO - REUMATOLOGÍA PEDIÁTRICA", styles['Titulo']))
    elementos.append(Spacer(1, 0.5*cm))
    
    # Datos del paciente
    elementos.append(Paragraph("DATOS DEL PACIENTE", styles['Subtitulo']))
    datos_pac = [
        ["Nombre:", paciente.get("nombre", "-")],
        ["NHC:", paciente.get("numero_historia", "-")],
        ["Fecha Nacimiento:", paciente.get("fecha_nacimiento", "-")],
        ["Edad:", f"{paciente.get('edad', '-')} años"],
        ["Diagnóstico:", paciente.get("diagnostico", "-")],
    ]
    tabla_pac = Table(datos_pac, colWidths=[4*cm, 10*cm])
    tabla_pac.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elementos.append(tabla_pac)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Perfil inmunológico
    perfil = paciente.get("perfil_inmuno", {})
    if perfil:
        elementos.append(Paragraph("PERFIL INMUNOLÓGICO", styles['Subtitulo']))
        perfil_texto = f"ANA: {perfil.get('ana', '-')} | FR: {perfil.get('fr', '-')} | ACPA: {perfil.get('acpa', '-')} | HLA-B27: {perfil.get('hla', '-')}"
        elementos.append(Paragraph(perfil_texto, styles['Normal2']))
        elementos.append(Spacer(1, 0.3*cm))
    
    # Última visita o visita seleccionada
    visita = visita_seleccionada
    if not visita and historial:
        visita = historial[-1] if isinstance(historial[-1], dict) else None
    
    if visita:
        elementos.append(Paragraph(f"ÚLTIMA EVOLUCIÓN ({visita.get('fecha', '-')})", styles['Subtitulo']))
        
        # Anamnesis
        if visita.get("anamnesis"):
            elementos.append(Paragraph(f"<b>Anamnesis:</b> {visita.get('anamnesis')}", styles['Normal2']))
        
        # Exploración
        exp = visita.get("exploracion", {})
        if exp:
            exp_texto = f"NAD: {exp.get('nad', '-')} | NAT: {exp.get('nat', '-')} | EVA: {exp.get('eva', '-')}"
            elementos.append(Paragraph(f"<b>Exploración:</b> {exp_texto}", styles['Normal2']))
            
            arts = exp.get("arts_activas", [])
            if arts:
                elementos.append(Paragraph(f"<b>Articulaciones activas:</b> {', '.join(arts)}", styles['Normal2']))
        
        # Analítica
        ana = visita.get("analitica", {})
        if ana and any(ana.values()):
            ana_texto = f"Hb: {ana.get('hb', '-')} | VSG: {ana.get('vsg', '-')} | PCR: {ana.get('pcr', '-')} | Calprotectina: {ana.get('calpro', '-')}"
            elementos.append(Paragraph(f"<b>Analítica:</b> {ana_texto}", styles['Normal2']))
        
        # Plan
        if visita.get("plan_tratamiento"):
            elementos.append(Spacer(1, 0.3*cm))
            elementos.append(Paragraph(f"<b>Plan terapéutico:</b>", styles['Normal2']))
            elementos.append(Paragraph(visita.get("plan_tratamiento"), styles['Normal2']))
    
    # Pie de página
    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph(f"Informe generado el {date.today().strftime('%d/%m/%Y')}", styles['Normal2']))
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# --- FUNCIÓN AUXILIAR PARA CALCULAR FRECUENCIAS ---
def calcular_frecuencia_historica(historial):
    """Recorre el historial y cuenta las apariciones de cada articulación."""
    conteo = {}
    if not historial:
        return conteo
        
    for visita in historial:
        if isinstance(visita, dict):
            arts = []
            
            # 1. Buscar en exploracion -> arts_activas (formato actual)
            exp = visita.get("exploracion", {})
            if isinstance(exp, dict):
                arts = exp.get("arts_activas", []) or exp.get("articulaciones_activas", [])
            
            # 2. Buscar en el nivel raíz (formato antiguo)
            if not arts:
                arts = visita.get("arts_activas", [])
            
            # 3. Buscar articulaciones_afectadas (datos basales)
            if not arts:
                 arts = visita.get("articulaciones_afectadas", [])
            
            # 4. Contar
            if arts:
                for art_nombre in arts:
                    conteo[art_nombre] = conteo.get(art_nombre, 0) + 1
    
    # Debug
    if conteo:
        print(f"🔥 Frecuencias calculadas: {conteo}")
    
    return conteo

# ==============================================================================
# 📝 VENTANA DE EDICIÓN DE DATOS BASALES
# ==============================================================================
@st.dialog("✏️ Modificar Datos del Paciente")
def editar_datos_paciente(paciente):
    """Formulario simplificado para editar filiación, biometría y diagnóstico."""
    
    # --- 1. Identificación ---
    c_id1, c_id2 = st.columns([1, 2])
    new_nhc = c_id1.text_input("NHC", value=paciente["numero_historia"])
    new_nombre = c_id2.text_input("Nombre", value=paciente["nombre"])
    
    st.markdown("---")
    
    # --- 2. Biometría ---
    st.markdown("##### 📏 Biometría")
    c1, c2, c3 = st.columns(3)
    
    try:
        f_nac_default = datetime.strptime(paciente["fecha_nacimiento"], "%Y-%m-%d").date()
    except:
        f_nac_default = date.today()

    f_nac = c1.date_input("Nacimiento", value=f_nac_default)
    sexo = c2.selectbox("Sexo", ["Mujer", "Hombre"], index=0 if paciente.get("sexo") == "Mujer" else 1)
    
    c_p, c_t = st.columns(2)
    peso = c_p.number_input("Peso (kg)", value=float(paciente["peso_actual"]))
    talla = c_t.number_input("Talla (cm)", value=float(paciente.get("talla", 100.0)))
    
    # Recalcular BSA
    bsa = math.sqrt((peso * talla) / 3600) if peso > 0 and talla > 0 else 0.0
    st.caption(f"S. Corporal (BSA) recalculada: **{bsa:.2f} m²**")
    
    st.markdown("---")
    
    # --- 3. Diagnóstico y Uveítis ---
    st.markdown("##### 🩺 Diagnóstico")
    
    tipos_diag = ["AIJ sistémica", "AIJ oligoarticular", "AIJ poliarticular", "Artritis psoriásica", "Entesitis", "Indiferenciada"]
    idx_diag = 0
    raw_diag = paciente["diagnostico"].split(" (")[0]
    if raw_diag in tipos_diag:
        idx_diag = tipos_diag.index(raw_diag)
    
    tipo = st.selectbox("Tipo", tipos_diag, index=idx_diag)
    
    try:
        f_sint_default = datetime.strptime(paciente.get("fecha_sintomas", str(date.today())), "%Y-%m-%d").date()
    except:
        f_sint_default = date.today()
        
    f_sintomas = st.date_input("Inicio Síntomas", value=f_sint_default)
    historia_uveitis = st.toggle("Antecedentes Uveítis", value=paciente.get("historia_uveitis", False))
    
    st.markdown("---")

    # --- 4. Anticuerpos ---
    st.markdown("##### 🧬 Anticuerpos")
    old_inmuno = paciente.get("perfil_inmuno", {})
    
    def radio_edit(label, key_name, old_dict):
        val_antiguo = old_dict.get(key_name, "Negativo (-)") 
        idx = 1 if "Positivo" in val_antiguo else 0
        return st.radio(label, ["Negativo (-)", "Positivo (+)"], index=idx, horizontal=True, key=f"edit_{key_name}")

    e_fr = radio_edit("FR", "fr", old_inmuno)
    e_acpa = radio_edit("ACPA", "acpa", old_inmuno)
    e_hla = radio_edit("HLA-B27", "hla", old_inmuno)
    e_ana = radio_edit("ANA", "ana", old_inmuno)
    
    st.markdown("###")
    
    # --- BOTONES DE ACCIÓN ---
    col_save, col_del = st.columns([3, 1])
    
    with col_save:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            pos = []
            if "Positivo" in e_fr: pos.append("FR+")
            if "Positivo" in e_acpa: pos.append("ACPA+")
            if "Positivo" in e_hla: pos.append("HLA-B27+")
            if "Positivo" in e_ana: pos.append("ANA+")
            diag_fin = f"{tipo} ({', '.join(pos)})" if pos else tipo
            
            riesgo = "Muy Alto (Recurrente)" if historia_uveitis else ("Alto" if "Positivo" in e_ana else "Bajo")

            # Actualizamos
            paciente["numero_historia"] = new_nhc
            paciente["nombre"] = new_nombre
            paciente["fecha_nacimiento"] = str(f_nac)
            paciente["edad"] = date.today().year - f_nac.year
            paciente["sexo"] = sexo
            paciente["peso_actual"] = peso
            paciente["talla"] = talla
            paciente["bsa"] = round(bsa, 2)
            paciente["diagnostico"] = diag_fin
            paciente["fecha_sintomas"] = str(f_sintomas)
            paciente["historia_uveitis"] = historia_uveitis
            paciente["perfil_inmuno"] = {"fr": e_fr, "acpa": e_acpa, "hla": e_hla, "ana": e_ana}
            paciente["ana"] = e_ana
            paciente["fr"] = e_fr
            paciente["riesgo_uveitis"] = riesgo
            
            guardar_paciente(paciente)
            st.success("✅ Datos actualizados")
            time.sleep(1)
            st.rerun()

    with col_del:
        if st.button("🗑️ Borrar", type="primary", help="Eliminar paciente permanentemente"):
            borrar_paciente_db(paciente["id"])
            st.warning("Paciente eliminado.")
            time.sleep(1)
            st.rerun()


# ==============================================================================
# 🖥️ RENDERIZADO DEL DASHBOARD PRINCIPAL
# ==============================================================================
def render_dashboard(paciente_sel, ir_a_visita_callback=None):
    # Cargar historial para ver si tiene visitas
    historial = cargar_historial_medico(paciente_sel["id"])
    tiene_visitas = len(historial) > 0
    
    # Calcular mapa de calor si hay datos
    frecuencias_heatmap = {}
    if tiene_visitas:
        frecuencias_heatmap = calcular_frecuencia_historica(historial)

    # --- 🚨 SISTEMA DE ALERTAS ---
    alertas = generar_alertas(paciente_sel, historial)
    if alertas:
        with st.container(border=True):
            st.markdown("### 🚨 Alertas Clínicas")
            
            # Inicializar estado de checkboxes
            if "alertas_seleccionadas" not in st.session_state:
                st.session_state.alertas_seleccionadas = set()
            
            for alerta in alertas:
                col_check, col_texto = st.columns([0.08, 0.92])
                
                with col_check:
                    checked = st.checkbox(
                        "", 
                        key=f"alert_{alerta['id']}", 
                        value=alerta['id'] in st.session_state.alertas_seleccionadas
                    )
                    if checked:
                        st.session_state.alertas_seleccionadas.add(alerta['id'])
                    else:
                        st.session_state.alertas_seleccionadas.discard(alerta['id'])
                
                with col_texto:
                    if alerta["urgencia"] == "alta":
                        st.error(alerta["texto"])
                    elif alerta["urgencia"] == "media":
                        st.warning(alerta["texto"])
                    else:
                        st.info(alerta["texto"])
            
            # Botón para marcar como resueltas
            if st.session_state.alertas_seleccionadas:
                st.markdown("---")
                if st.button("✅ Marcar seleccionadas como resueltas", type="primary", use_container_width=True):
                    for alerta_id in list(st.session_state.alertas_seleccionadas):
                        marcar_alerta_resuelta(paciente_sel, alerta_id)
                    st.session_state.alertas_seleccionadas = set()
                    st.success("Alertas marcadas como resueltas")
                    time.sleep(0.5)
                    st.rerun()
        st.markdown("")

    # --- LAYOUT SUPERIOR COMPACTO ---
    # Header: Nombre + Botones
    col_header, col_btn = st.columns([5, 1])
    
    with col_header:
        st.markdown(f"## {paciente_sel['nombre']} | {paciente_sel.get('numero_historia')}")
        st.caption(f"{paciente_sel['diagnostico']} | {paciente_sel.get('bsa', '-')} m²")
        
        # Perfil Autoinmune como badges horizontales
        perfil = paciente_sel.get("perfil_inmuno", {})
        if perfil:
            badges_html = "<div style='display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;'>"
            for ab, key in [("ANA", "ana"), ("FR", "fr"), ("ACPA", "acpa"), ("HLA-B27", "hla")]:
                valor = perfil.get(key, "")
                if "Positivo" in valor or "+" in valor:
                    badges_html += f"<span style='background:#fee2e2; color:#991b1b; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.85rem;'>● {ab}+</span>"
                else:
                    badges_html += f"<span style='background:#f3f4f6; color:#9ca3af; padding:4px 12px; border-radius:20px; font-size:0.85rem;'>○ {ab}−</span>"
            badges_html += "</div>"
            st.markdown(badges_html, unsafe_allow_html=True)
    
    with col_btn:
        if st.button("➕ Nueva Visita", type="primary", use_container_width=True): 
            if ir_a_visita_callback:
                ir_a_visita_callback()
        
        if not tiene_visitas:
            if st.button("✏️ Modificar", type="secondary", key="btn_edit_main", use_container_width=True):
                editar_datos_paciente(paciente_sel)
        else:
            st.button("🔒 Bloqueado", disabled=True, use_container_width=True,
                      help="Paciente con historial. Contacte admin para modificar.")
    
    st.markdown("---")
    
    # --- 📢 ÚLTIMO CURSO CLÍNICO (NUEVA SECCIÓN) ---
    if "ultimo_curso_clinico" in paciente_sel:
        with st.expander("📄 Último Curso Clínico (Resumen)", expanded=True):
            st.info(paciente_sel["ultimo_curso_clinico"])
        st.markdown("---")
    # ------------------------------------------------

    # --- 📱 DATOS DEL PACIENTE (CHAQ y Fotos) ---
    chaq_data = paciente_sel.get("cuestionarios_chaq", [])
    fotos_data = paciente_sel.get("fotos_articulaciones", [])
    
    if chaq_data or fotos_data:
        with st.container(border=True):
            st.markdown("### 📱 Datos reportados por el paciente")
            
            col_chaq, col_fotos = st.columns(2)
            
            with col_chaq:
                if chaq_data:
                    ultimo_chaq = chaq_data[-1]
                    st.markdown("**📋 Último CHAQ**")
                    st.caption(f"Fecha: {ultimo_chaq['fecha']}")
                    
                    # Métricas
                    c1, c2, c3 = st.columns(3)
                    score = ultimo_chaq.get("score", 0)
                    
                    # Interpretación
                    if score == 0:
                        interp = "Sin discapacidad"
                        color = "#22c55e"
                    elif score < 0.5:
                        interp = "Mínima"
                        color = "#22c55e"
                    elif score < 1.0:
                        interp = "Leve"
                        color = "#eab308"
                    elif score < 2.0:
                        interp = "Moderada"
                        color = "#f97316"
                    else:
                        interp = "Severa"
                        color = "#ef4444"
                    
                    c1.metric("CHAQ Score", f"{score:.2f}")
                    c2.metric("EVA Dolor", ultimo_chaq.get("eva_dolor", "-"))
                    c3.metric("EVA Global", ultimo_chaq.get("eva_global", "-"))
                    st.markdown(f"<span style='color:{color}; font-weight:bold;'>{interp}</span>", unsafe_allow_html=True)
                    
                    # Histórico si hay más de uno
                    if len(chaq_data) > 1:
                        with st.expander(f"📊 Histórico ({len(chaq_data)} registros)"):
                            df_chaq = pd.DataFrame([
                                {"Fecha": c["fecha"], "CHAQ": c["score"], "EVA Dolor": c.get("eva_dolor", 0)}
                                for c in chaq_data
                            ])
                            df_chaq["Fecha"] = pd.to_datetime(df_chaq["Fecha"])
                            
                            chart_chaq = alt.Chart(df_chaq).mark_line(point=True, strokeWidth=2, color="#C41E3A").encode(
                                x=alt.X("Fecha:T", title="Fecha"),
                                y=alt.Y("CHAQ:Q", title="Score CHAQ", scale=alt.Scale(domain=[0, 3])),
                                tooltip=["Fecha:T", "CHAQ:Q", "EVA Dolor:Q"]
                            ).properties(height=150)
                            st.altair_chart(chart_chaq, use_container_width=True)
                else:
                    st.caption("📋 Sin cuestionarios CHAQ")
            
            with col_fotos:
                # Homúnculo con patrón de afectación histórico
                st.markdown("**🦴 Patrón Articular**")
                if tiene_visitas and HEATMAP_OK:
                    renderizar_heatmap_dashboard(frecuencias_heatmap)
                else:
                    st.caption("Sin histórico articular")
    st.markdown("---")

    t1, t2, t3, t4, t5 = st.tabs(["📏 Biometría", "📊 Actividad", "🔬 Analíticas", "⚠️ Efectos Adversos", "📋 Historial"])
    
    with t1:
        # Obtener sexo del paciente para percentiles
        sexo_pac = paciente_sel.get("sexo", "M")
        edad_actual = paciente_sel.get("edad", 10)
        
        # Toggle para ver curvas OMS
        mostrar_percentiles = st.checkbox("📈 Mostrar curvas percentiles OMS", value=True)
        
        col_peso, col_talla = st.columns(2)
        
        with col_peso:
            st.markdown("**Peso (kg)**")
            h_peso = paciente_sel.get("historial_peso", {})
            
            if h_peso:
                # Preparar datos del paciente con edad aproximada en cada fecha
                fecha_nac = paciente_sel.get("fecha_nacimiento")
                df_peso = pd.DataFrame(list(h_peso.items()), columns=["Fecha", "Peso"])
                df_peso["Fecha"] = pd.to_datetime(df_peso["Fecha"])
                
                # Calcular edad en cada fecha
                if fecha_nac:
                    try:
                        fn = pd.to_datetime(fecha_nac)
                        df_peso["Edad"] = ((df_peso["Fecha"] - fn).dt.days / 365.25).round(1)
                    except:
                        df_peso["Edad"] = edad_actual
                else:
                    # Aproximar edad basada en edad actual
                    fecha_mas_reciente = df_peso["Fecha"].max()
                    df_peso["Edad"] = edad_actual - ((fecha_mas_reciente - df_peso["Fecha"]).dt.days / 365.25)
                
                df_peso["Edad"] = df_peso["Edad"].clip(2, 18)
                
                # Mostrar percentil actual
                peso_actual = df_peso["Peso"].iloc[-1]
                edad_para_percentil = df_peso["Edad"].iloc[-1]
                _, percentil_texto = calcular_percentil(peso_actual, edad_para_percentil, sexo_pac, "peso")
                st.caption(f"Actual: **{peso_actual:.1f} kg** ({percentil_texto})")
                
                if mostrar_percentiles:
                    # Curvas de percentiles
                    edad_min = max(2, int(df_peso["Edad"].min()) - 1)
                    edad_max = min(18, int(df_peso["Edad"].max()) + 2)
                    df_curvas = generar_curvas_percentiles(sexo_pac, "peso", edad_min, edad_max)
                    
                    # Colores para percentiles
                    colores_p = {"P3": "#fee2e2", "P15": "#fef3c7", "P50": "#d1fae5", "P85": "#fef3c7", "P97": "#fee2e2"}
                    
                    base = alt.Chart(df_curvas).mark_line(strokeDash=[4,4], strokeWidth=1).encode(
                        x=alt.X("Edad:Q", title="Edad (años)", scale=alt.Scale(domain=[edad_min, edad_max])),
                        y=alt.Y("Valor:Q", title="Kg"),
                        color=alt.Color("Percentil:N", scale=alt.Scale(
                            domain=["P3", "P15", "P50", "P85", "P97"],
                            range=["#ef4444", "#f59e0b", "#22c55e", "#f59e0b", "#ef4444"]
                        ), legend=alt.Legend(title="Percentil", orient="bottom"))
                    )
                    
                    # Datos del paciente
                    puntos = alt.Chart(df_peso).mark_line(point=True, strokeWidth=3, color="#3b82f6").encode(
                        x="Edad:Q",
                        y=alt.Y("Peso:Q"),
                        tooltip=[alt.Tooltip("Fecha:T", format="%d/%m/%Y"), "Peso:Q", "Edad:Q"]
                    )
                    
                    st.altair_chart((base + puntos).properties(height=280), use_container_width=True)
                else:
                    peso_max = max(50, df_peso["Peso"].max() + 5)
                    chart_peso = alt.Chart(df_peso).mark_line(point=True, strokeWidth=2, color="#3b82f6").encode(
                        x=alt.X("Fecha:T", title="Fecha", axis=alt.Axis(format="%b %Y")),
                        y=alt.Y("Peso:Q", title="Kg", scale=alt.Scale(domain=[0, peso_max])),
                        tooltip=["Fecha:T", "Peso:Q"]
                    ).properties(height=250)
                    st.altair_chart(chart_peso, use_container_width=True)
            else:
                st.caption("Sin datos de peso")
        
        with col_talla:
            st.markdown("**Talla (cm)**")
            h_talla = paciente_sel.get("historial_talla", {})
            
            if h_talla:
                fecha_nac = paciente_sel.get("fecha_nacimiento")
                df_talla = pd.DataFrame(list(h_talla.items()), columns=["Fecha", "Talla"])
                df_talla["Fecha"] = pd.to_datetime(df_talla["Fecha"])
                
                # Calcular edad en cada fecha
                if fecha_nac:
                    try:
                        fn = pd.to_datetime(fecha_nac)
                        df_talla["Edad"] = ((df_talla["Fecha"] - fn).dt.days / 365.25).round(1)
                    except:
                        df_talla["Edad"] = edad_actual
                else:
                    fecha_mas_reciente = df_talla["Fecha"].max()
                    df_talla["Edad"] = edad_actual - ((fecha_mas_reciente - df_talla["Fecha"]).dt.days / 365.25)
                
                df_talla["Edad"] = df_talla["Edad"].clip(2, 18)
                
                # Mostrar percentil actual
                talla_actual = df_talla["Talla"].iloc[-1]
                edad_para_percentil = df_talla["Edad"].iloc[-1]
                _, percentil_texto = calcular_percentil(talla_actual, edad_para_percentil, sexo_pac, "talla")
                st.caption(f"Actual: **{talla_actual:.0f} cm** ({percentil_texto})")
                
                if mostrar_percentiles:
                    edad_min = max(2, int(df_talla["Edad"].min()) - 1)
                    edad_max = min(18, int(df_talla["Edad"].max()) + 2)
                    df_curvas = generar_curvas_percentiles(sexo_pac, "talla", edad_min, edad_max)
                    
                    base = alt.Chart(df_curvas).mark_line(strokeDash=[4,4], strokeWidth=1).encode(
                        x=alt.X("Edad:Q", title="Edad (años)", scale=alt.Scale(domain=[edad_min, edad_max])),
                        y=alt.Y("Valor:Q", title="cm"),
                        color=alt.Color("Percentil:N", scale=alt.Scale(
                            domain=["P3", "P15", "P50", "P85", "P97"],
                            range=["#ef4444", "#f59e0b", "#22c55e", "#f59e0b", "#ef4444"]
                        ), legend=alt.Legend(title="Percentil", orient="bottom"))
                    )
                    
                    puntos = alt.Chart(df_talla).mark_line(point=True, strokeWidth=3, color="#10b981").encode(
                        x="Edad:Q",
                        y=alt.Y("Talla:Q"),
                        tooltip=[alt.Tooltip("Fecha:T", format="%d/%m/%Y"), "Talla:Q", "Edad:Q"]
                    )
                    
                    st.altair_chart((base + puntos).properties(height=280), use_container_width=True)
                else:
                    talla_max = max(140, df_talla["Talla"].max() + 10)
                    chart_talla = alt.Chart(df_talla).mark_line(point=True, strokeWidth=2, color="#10b981").encode(
                        x=alt.X("Fecha:T", title="Fecha", axis=alt.Axis(format="%b %Y")),
                        y=alt.Y("Talla:Q", title="cm", scale=alt.Scale(domain=[0, talla_max])),
                        tooltip=["Fecha:T", "Talla:Q"]
                    ).properties(height=250)
                    st.altair_chart(chart_talla, use_container_width=True)
            else:
                st.caption("Sin datos de talla")
    
    with t2:
        # --- GRÁFICAS DE ACTIVIDAD DE ENFERMEDAD ---
        st.markdown("**Actividad de Enfermedad**")
        
        # Extraer NAT, NAD, EVA y calcular JADAS de cada visita
        datos_actividad = []
        for visita in historial:
            if isinstance(visita, dict):
                fecha = visita.get("fecha")
                exp = visita.get("exploracion", {})
                
                # Extraer NAT y NAD
                nat = exp.get("nat") if isinstance(exp, dict) else None
                nad = exp.get("nad") if isinstance(exp, dict) else None
                eva_med = exp.get("eva") if isinstance(exp, dict) else None
                eva_pac = visita.get("eva_paciente") or exp.get("eva_paciente") if isinstance(exp, dict) else None
                
                # Extraer VSG para JADAS
                analitica = visita.get("analitica", {}) or exp.get("analitica", {}) if isinstance(exp, dict) else {}
                vsg = None
                try:
                    vsg_str = analitica.get("vsg", "") if isinstance(analitica, dict) else ""
                    vsg = float(str(vsg_str).replace(",", ".")) if vsg_str else None
                except:
                    pass
                
                # Calcular JADAS si tenemos datos suficientes
                jadas = None
                if nat is not None and eva_med is not None:
                    nad_score = min(float(nad or 0), 27)
                    eva_med_score = min(max(float(eva_med or 0), 0), 10)
                    eva_pac_score = min(max(float(eva_pac or 0), 0), 10) if eva_pac else 0
                    marcador = max(0, min(10, (float(vsg) - 20) / 10)) if vsg else 0
                    jadas = round(nad_score + eva_med_score + eva_pac_score + marcador, 1)
                
                if fecha and (nat is not None or nad is not None or jadas is not None):
                    datos_actividad.append({
                        "Fecha": fecha,
                        "NAT": nat,
                        "NAD": nad,
                        "EVA": eva_med,
                        "JADAS": jadas
                    })
        
        if datos_actividad:
            df_actividad = pd.DataFrame(datos_actividad)
            df_actividad["Fecha"] = pd.to_datetime(df_actividad["Fecha"])
            df_actividad = df_actividad.sort_values("Fecha")
            
            # Gráfica NAT/NAD
            col_nat, col_jadas = st.columns(2)
            
            with col_nat:
                st.markdown("**NAT / NAD (Articulaciones)**")
                df_nat = df_actividad[df_actividad["NAT"].notna() | df_actividad["NAD"].notna()].copy()
                
                if not df_nat.empty:
                    # Preparar datos para gráfica con dos líneas
                    df_melted = df_nat.melt(id_vars=["Fecha"], value_vars=["NAT", "NAD"], 
                                           var_name="Tipo", value_name="Valor")
                    df_melted = df_melted[df_melted["Valor"].notna()]
                    
                    nat_max = max(10, df_melted["Valor"].max() + 2)
                    
                    chart_nat = alt.Chart(df_melted).mark_line(
                        point=True, strokeWidth=2
                    ).encode(
                        x=alt.X("Fecha:T", title="", axis=alt.Axis(format="%b %Y")),
                        y=alt.Y("Valor:Q", title="Nº articulaciones", scale=alt.Scale(domain=[0, nat_max])),
                        color=alt.Color("Tipo:N", scale=alt.Scale(
                            domain=["NAT", "NAD"],
                            range=["#ef4444", "#f97316"]  # Rojo y naranja
                        )),
                        tooltip=["Fecha:T", "Tipo:N", "Valor:Q"]
                    ).properties(height=200)
                    
                    st.altair_chart(chart_nat, use_container_width=True)
                    st.caption("🔴 NAT (tumefactas) | 🟠 NAD (dolorosas)")
                else:
                    st.caption("Sin datos de exploración articular")
            
            with col_jadas:
                st.markdown("**JADAS-27 (Score de Actividad)**")
                df_jadas = df_actividad[df_actividad["JADAS"].notna()].copy()
                
                if not df_jadas.empty:
                    jadas_max = max(20, df_jadas["JADAS"].max() + 2)
                    
                    # Zonas de color de fondo
                    zonas = pd.DataFrame({
                        "y": [0, 1, 3.8, 10.5],
                        "y2": [1, 3.8, 10.5, jadas_max],
                        "color": ["Remisión", "Baja", "Moderada", "Alta"]
                    })
                    
                    fondo = alt.Chart(zonas).mark_rect(opacity=0.2).encode(
                        y=alt.Y("y:Q", scale=alt.Scale(domain=[0, jadas_max])),
                        y2="y2:Q",
                        color=alt.Color("color:N", scale=alt.Scale(
                            domain=["Remisión", "Baja", "Moderada", "Alta"],
                            range=["#22c55e", "#eab308", "#f97316", "#ef4444"]
                        ), legend=None)
                    )
                    
                    linea_jadas = alt.Chart(df_jadas).mark_line(
                        point=True, strokeWidth=3, color="#1e40af"
                    ).encode(
                        x=alt.X("Fecha:T", title="", axis=alt.Axis(format="%b %Y")),
                        y=alt.Y("JADAS:Q", title="JADAS-27", scale=alt.Scale(domain=[0, jadas_max])),
                        tooltip=["Fecha:T", "JADAS:Q"]
                    ).properties(height=200)
                    
                    st.altair_chart(fondo + linea_jadas, use_container_width=True)
                    st.caption("🟢 Remisión (≤1) | 🟡 Baja | 🟠 Moderada | 🔴 Alta (>10.5)")
                else:
                    st.caption("Sin datos de JADAS")
            
            # Tabla resumen de última visita
            if len(df_actividad) > 0:
                ultima = df_actividad.iloc[-1]
                st.markdown("---")
                st.markdown("**Última visita:**")
                cols = st.columns(4)
                cols[0].metric("NAT", int(ultima["NAT"]) if pd.notna(ultima["NAT"]) else "-")
                cols[1].metric("NAD", int(ultima["NAD"]) if pd.notna(ultima["NAD"]) else "-")
                cols[2].metric("EVA", ultima["EVA"] if pd.notna(ultima["EVA"]) else "-")
                if pd.notna(ultima["JADAS"]):
                    jadas_val = ultima["JADAS"]
                    if jadas_val <= 1:
                        interp = "Remisión 🟢"
                    elif jadas_val <= 3.8:
                        interp = "Baja 🟡"
                    elif jadas_val <= 10.5:
                        interp = "Moderada 🟠"
                    else:
                        interp = "Alta 🔴"
                    cols[3].metric("JADAS-27", f"{jadas_val}", delta=interp, delta_color="off")
                else:
                    cols[3].metric("JADAS-27", "-")
        else:
            st.info("No hay datos de actividad de enfermedad. Registra visitas con exploración articular.")
    
    with t3:
        # --- GRÁFICAS DE MARCADORES INFLAMATORIOS ---
        st.markdown("**Marcadores Inflamatorios**")
        
        # Extraer PCR, VSG y Calprotectina del historial de visitas
        datos_analitica = []
        for visita in historial:
            if isinstance(visita, dict):
                fecha = visita.get("fecha")
                analitica = visita.get("analitica", {})
                
                # También buscar en exploracion.analitica (formato alternativo)
                if not analitica or (not analitica.get("pcr") and not analitica.get("vsg")):
                    analitica = visita.get("exploracion", {}).get("analitica", {})
                
                pcr_str = analitica.get("pcr", "")
                vsg_str = analitica.get("vsg", "")
                calpro_str = analitica.get("calpro", "") or analitica.get("calprotectina", "")
                
                # Convertir a float si es posible
                def to_float(s):
                    try:
                        return float(str(s).replace(",", ".")) if s else None
                    except:
                        return None
                
                pcr = to_float(pcr_str)
                vsg = to_float(vsg_str)
                calpro = to_float(calpro_str)
                
                if fecha and (pcr is not None or vsg is not None or calpro is not None):
                    datos_analitica.append({
                        "Fecha": fecha,
                        "PCR": pcr,
                        "VSG": vsg,
                        "Calprotectina": calpro
                    })
        
        if datos_analitica:
            df_analitica = pd.DataFrame(datos_analitica)
            df_analitica["Fecha"] = pd.to_datetime(df_analitica["Fecha"])
            df_analitica = df_analitica.sort_values("Fecha")
            
            col_pcr, col_vsg, col_calpro = st.columns(3)
            
            with col_pcr:
                st.markdown("**PCR (mg/L)**")
                df_pcr = df_analitica[df_analitica["PCR"].notna()].copy()
                if not df_pcr.empty:
                    pcr_max = max(15, df_pcr["PCR"].max() + 2)
                    
                    linea_ref = alt.Chart(pd.DataFrame({"y": [5]})).mark_rule(
                        color="orange", strokeDash=[4, 4], strokeWidth=1
                    ).encode(y="y:Q")
                    
                    chart_pcr = alt.Chart(df_pcr).mark_line(
                        point=True, strokeWidth=2, color="#ef4444"
                    ).encode(
                        x=alt.X("Fecha:T", title="", axis=alt.Axis(format="%b")),
                        y=alt.Y("PCR:Q", title="mg/L", scale=alt.Scale(domain=[0, pcr_max])),
                        tooltip=["Fecha:T", "PCR:Q"]
                    ).properties(height=180)
                    
                    st.altair_chart(chart_pcr + linea_ref, use_container_width=True)
                    st.caption("Normal: <5")
                else:
                    st.caption("Sin datos")
            
            with col_vsg:
                st.markdown("**VSG (mm/h)**")
                df_vsg = df_analitica[df_analitica["VSG"].notna()].copy()
                if not df_vsg.empty:
                    vsg_max = max(50, df_vsg["VSG"].max() + 5)
                    
                    linea_ref_vsg = alt.Chart(pd.DataFrame({"y": [20]})).mark_rule(
                        color="orange", strokeDash=[4, 4], strokeWidth=1
                    ).encode(y="y:Q")
                    
                    chart_vsg = alt.Chart(df_vsg).mark_line(
                        point=True, strokeWidth=2, color="#8b5cf6"
                    ).encode(
                        x=alt.X("Fecha:T", title="", axis=alt.Axis(format="%b")),
                        y=alt.Y("VSG:Q", title="mm/h", scale=alt.Scale(domain=[0, vsg_max])),
                        tooltip=["Fecha:T", "VSG:Q"]
                    ).properties(height=180)
                    
                    st.altair_chart(chart_vsg + linea_ref_vsg, use_container_width=True)
                    st.caption("Normal: <20")
                else:
                    st.caption("Sin datos")
            
            with col_calpro:
                st.markdown("**Calprotectina (µg/g)**")
                df_calpro = df_analitica[df_analitica["Calprotectina"].notna()].copy()
                if not df_calpro.empty:
                    calpro_max = max(200, df_calpro["Calprotectina"].max() + 20)
                    
                    # Calprotectina normal <50 µg/g
                    linea_ref_calpro = alt.Chart(pd.DataFrame({"y": [50]})).mark_rule(
                        color="orange", strokeDash=[4, 4], strokeWidth=1
                    ).encode(y="y:Q")
                    
                    chart_calpro = alt.Chart(df_calpro).mark_line(
                        point=True, strokeWidth=2, color="#f59e0b"
                    ).encode(
                        x=alt.X("Fecha:T", title="", axis=alt.Axis(format="%b")),
                        y=alt.Y("Calprotectina:Q", title="µg/g", scale=alt.Scale(domain=[0, calpro_max])),
                        tooltip=["Fecha:T", "Calprotectina:Q"]
                    ).properties(height=180)
                    
                    st.altair_chart(chart_calpro + linea_ref_calpro, use_container_width=True)
                    st.caption("Normal: <50")
                else:
                    st.caption("Sin datos")
        else:
            st.info("No hay datos analíticos registrados en las visitas.")
        
        # --- BOTÓN EXPORTAR PDF ---
        st.markdown("---")
        col_pdf, _ = st.columns([1, 2])
        with col_pdf:
            if PDF_DISPONIBLE:
                if st.button("📄 Exportar Informe PDF", use_container_width=True):
                    pdf_buffer = generar_pdf_informe(paciente_sel, historial)
                    if pdf_buffer:
                        st.download_button(
                            label="⬇️ Descargar PDF",
                            data=pdf_buffer,
                            file_name=f"Informe_{paciente_sel.get('nombre', 'paciente').replace(' ', '_')}_{date.today().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
            else:
                st.caption("📄 PDF no disponible (instalar reportlab)")
    
    with t4:
        # --- EFECTOS ADVERSOS ---
        st.markdown("**Historial de Efectos Adversos**")
        
        efectos_todos = []
        for visita in historial:
            if isinstance(visita, dict):
                fecha = visita.get("fecha", "")
                efectos = visita.get("efectos_adversos", [])
                for ef in efectos:
                    ef["fecha_visita"] = fecha
                    efectos_todos.append(ef)
        
        if efectos_todos:
            # Ordenar por fecha descendente
            efectos_todos.sort(key=lambda x: x.get("fecha_visita", ""), reverse=True)
            
            # Conteo por medicación
            col_resumen, col_lista = st.columns([1, 2])
            
            with col_resumen:
                st.markdown("##### 📊 Resumen")
                from collections import Counter
                meds_count = Counter([e["medicacion"] for e in efectos_todos])
                grav_count = Counter([e["gravedad"] for e in efectos_todos])
                
                for med, count in meds_count.most_common():
                    st.caption(f"💊 **{med}**: {count} registro(s)")
                
                st.markdown("---")
                st.caption(f"🔴 Graves: {grav_count.get('Grave', 0)}")
                st.caption(f"🟠 Moderados: {grav_count.get('Moderado', 0)}")
                st.caption(f"🟡 Leves: {grav_count.get('Leve', 0)}")
            
            with col_lista:
                st.markdown("##### 📋 Detalle")
                for ef in efectos_todos:
                    color = "🔴" if ef["gravedad"] == "Grave" else ("🟠" if ef["gravedad"] == "Moderado" else "🟡")
                    efectos_txt = ", ".join(ef.get("efectos", [])) if ef.get("efectos") else ef.get("descripcion", "")
                    with st.container(border=True):
                        st.markdown(f"{color} **{ef['medicacion']}** - {ef.get('fecha_visita', '')}")
                        st.caption(f"{efectos_txt}")
                        if ef.get("descripcion") and ef.get("efectos"):
                            st.caption(f"*{ef['descripcion']}*")
        else:
            st.info("✅ No se han registrado efectos adversos")
    
    with t5:
        # Usamos la variable 'historial' que ya cargamos arriba
        for v in reversed(historial):
             if isinstance(v, dict):
                 f = v.get("fecha")
                 # Adaptamos para leer el nuevo formato de visita o el antiguo
                 tipo = v.get("tipo", "Visita")
                 plan = v.get("plan_tratamiento", "Sin cambios")
                 
                 # Si es formato antiguo (receta)
                 if "receta" in v:
                    r = v.get("receta", {}).get("tratamiento_secuencial", [{}])[0]
                    texto_header = f"{f} - {r.get('nombre')}"
                    texto_body = f"Dosis: {r.get('dosis_calculada')}"
                 else:
                    # Formato nuevo
                    texto_header = f"{f} - {tipo}"
                    texto_body = f"**Plan:** {plan}"

                 with st.expander(texto_header):
                     st.markdown(texto_body)
                     
                     # Mostrar curso completo si existe
                     if "curso_clinico_generado" in v:
                         st.divider()
                         st.caption("Nota completa:")
                         st.text(v["curso_clinico_generado"])
                     # Mostrar detalles extra antiguos si existen
                     elif "exploracion" in v:
                         e = v["exploracion"]
                         st.caption(f"NAD: {e.get('nad')} | NAT: {e.get('nat')} | EVA: {e.get('eva')}")


# ==============================================================================
# 🌐 DASHBOARD GLOBAL (VISTA DE TODOS LOS PACIENTES)
# ==============================================================================
def render_dashboard_global(todos_pacientes, seleccionar_paciente_callback=None):
    """
    Renderiza un dashboard global con vista de todos los pacientes,
    estadísticas, filtros y alertas pendientes.
    """
    from data_manager import cargar_historial_medico
    
    st.markdown("## 🏥 Dashboard Global")
    
    # Variables para filtros (se definen después de procesar datos)
    busqueda = ""
    filtro_diag = "Todos"
    filtro_trat = "Todos"
    filtro_alertas = "Todos"
    
    # --- PROCESAR DATOS DE TODOS LOS PACIENTES ---
    pacientes_procesados = []
    total_alertas = 0
    pacientes_brote = 0
    pacientes_remision = 0
    tratamientos = {"MTX": 0, "Biológico": 0, "Sin FAME": 0}
    
    for pid, pac in todos_pacientes.items():
        historial = cargar_historial_medico(pid)
        alertas = generar_alertas(pac, historial)
        total_alertas += len(alertas)
        
        # Obtener última visita
        ultima_visita = None
        nat_ultima = None
        jadas_ultimo = None
        ultimo_tratamiento = ""
        
        if historial:
            for visita in reversed(historial):
                if isinstance(visita, dict):
                    ultima_visita = visita.get("fecha")
                    exp = visita.get("exploracion", {})
                    if isinstance(exp, dict):
                        nat_ultima = exp.get("nat")
                    
                    plan = str(visita.get("plan_tratamiento", "")).lower()
                    if any(x in plan for x in ["metotrexato", "metotrexate", "mtx"]):
                        ultimo_tratamiento = "MTX"
                    elif any(x in plan for x in ["adalimumab", "etanercept", "tocilizumab", "humira"]):
                        ultimo_tratamiento = "Biológico"
                    break
        
        # Clasificar estado
        en_brote = nat_ultima is not None and nat_ultima > 0
        en_remision = nat_ultima is not None and nat_ultima == 0
        
        if en_brote:
            pacientes_brote += 1
        if en_remision:
            pacientes_remision += 1
        
        # Contar tratamientos
        if ultimo_tratamiento == "MTX":
            tratamientos["MTX"] += 1
        elif ultimo_tratamiento == "Biológico":
            tratamientos["Biológico"] += 1
        else:
            tratamientos["Sin FAME"] += 1
        
        pacientes_procesados.append({
            "id": pid,
            "paciente": pac,
            "nombre": pac.get("nombre", ""),
            "nhc": pac.get("numero_historia", ""),
            "diagnostico": pac.get("diagnostico", ""),
            "edad": pac.get("edad", 0),
            "ultima_visita": ultima_visita,
            "nat": nat_ultima,
            "alertas": len(alertas),
            "alertas_list": alertas,
            "tratamiento": ultimo_tratamiento,
            "en_brote": en_brote,
            "en_remision": en_remision
        })
    
    # --- MÉTRICAS GLOBALES (arriba) ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Pacientes", len(todos_pacientes))
    c2.metric("⚠️ Alertas", total_alertas)
    c3.metric("🔴 En Brote", pacientes_brote)
    c4.metric("🟢 En Remisión", pacientes_remision)
    
    st.markdown("---")
    
    # --- LAYOUT PRINCIPAL: Lista (izq) + Alertas (der) ---
    col_lista, col_alertas = st.columns([3, 1])
    
    with col_lista:
        # FILTROS inline
        st.markdown("### 📋 Lista de Pacientes")
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        with f1:
            busqueda = st.text_input("🔎 Buscar", placeholder="Nombre o NHC...", label_visibility="collapsed")
        with f2:
            diagnosticos = list(set([p.get("diagnostico", "").split(" (")[0] for p in todos_pacientes.values()]))
            diagnosticos = ["Todos"] + sorted([d for d in diagnosticos if d])
            filtro_diag = st.selectbox("Diagnóstico", diagnosticos, label_visibility="collapsed")
        with f3:
            filtro_trat = st.selectbox("Tratamiento", ["Todos", "MTX", "Biológico", "Sin FAME"], label_visibility="collapsed")
        with f4:
            filtro_alertas = st.selectbox("Estado", ["Todos", "⚠️ Alertas", "🔴 Brote", "🟢 Remisión"], label_visibility="collapsed")
        
        # APLICAR FILTROS
        pacientes_filtrados = pacientes_procesados.copy()
        
        if busqueda:
            busq_lower = busqueda.lower()
            pacientes_filtrados = [p for p in pacientes_filtrados 
                                  if busq_lower in p["nombre"].lower() or busq_lower in p["nhc"].lower()]
        
        if filtro_diag != "Todos":
            pacientes_filtrados = [p for p in pacientes_filtrados 
                                  if filtro_diag in p["diagnostico"]]
        
        if filtro_trat == "MTX":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["tratamiento"] == "MTX"]
        elif filtro_trat == "Biológico":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["tratamiento"] == "Biológico"]
        elif filtro_trat == "Sin FAME":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["tratamiento"] == ""]
        
        if filtro_alertas == "⚠️ Alertas":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["alertas"] > 0]
        elif filtro_alertas == "🔴 Brote":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["en_brote"]]
        elif filtro_alertas == "🟢 Remisión":
            pacientes_filtrados = [p for p in pacientes_filtrados if p["en_remision"]]
        
        st.caption(f"Mostrando {len(pacientes_filtrados)} de {len(todos_pacientes)} pacientes")
        
        # LISTA DE PACIENTES
        for p in pacientes_filtrados:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                
                with c1:
                    estado_icon = "🔴" if p["en_brote"] else ("🟢" if p["en_remision"] else "⚪")
                    st.markdown(f"**{estado_icon} {p['nombre']}**")
                    st.caption(f"NHC: {p['nhc']} | {p['edad']}a")
                
                with c2:
                    diag_corto = p["diagnostico"].split(" (")[0][:20]
                    st.caption(f"{diag_corto}")
                    if p["tratamiento"]:
                        st.caption(f"💊 {p['tratamiento']}")
                
                with c3:
                    if p["nat"] is not None:
                        color = "#ef4444" if p["nat"] > 0 else "#22c55e"
                        st.markdown(f"<div style='text-align:center;'><span style='font-size:1.3rem; color:{color};'>{p['nat']}</span><br><small>NAT</small></div>", unsafe_allow_html=True)
                    else:
                        st.caption("NAT: -")
                
                with c4:
                    if st.button("Abrir", key=f"open_{p['id']}", use_container_width=True):
                        if seleccionar_paciente_callback:
                            seleccionar_paciente_callback(p["paciente"])
    
    # COLUMNA DERECHA: ALERTAS
    with col_alertas:
        st.markdown("### 🚨 Alertas")
        pac_con_alertas = [p for p in pacientes_procesados if p["alertas"] > 0]
        
        if pac_con_alertas:
            for p in pac_con_alertas[:8]:
                with st.container(border=True):
                    st.markdown(f"**{p['nombre']}**")
                    for a in p["alertas_list"][:2]:
                        st.caption(a["texto"])
                    if st.button("→", key=f"alert_{p['id']}", use_container_width=True):
                        if seleccionar_paciente_callback:
                            seleccionar_paciente_callback(p["paciente"])
        else:
            st.success("✅ Sin alertas")