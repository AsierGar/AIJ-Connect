"""
================================================================================
DATA_MANAGER.PY - Gestor de Persistencia de Datos
================================================================================

Módulo que gestiona el almacenamiento y recuperación de datos de pacientes
e historial médico en archivos JSON.

ARCHIVOS DE DATOS:
- pacientes.json: Base de datos de pacientes (datos demográficos, diagnóstico)
- historial_pacientes.json: Registro de todas las visitas médicas

ESTRUCTURA DE PACIENTE:
{
    "id": "P_1",
    "numero_historia": "123456",
    "nombre": "Juan García",
    "fecha_nacimiento": "2015-03-20",
    "sexo": "Hombre",
    "peso_actual": 30.5,
    "diagnostico": "AIJ poliarticular (FR+)",
    "articulaciones_afectadas": ["Rodilla Der.", "Tobillo Izq."],
    ...
}

ESTRUCTURA DE HISTORIAL:
{
    "P_1": [
        {
            "fecha": "2025-01-15",
            "tipo": "visita",
            "jadas": 12,
            "articulaciones_activas": [...],
            "tratamiento": {...}
        },
        ...
    ]
}

FUNCIONES PRINCIPALES:
- cargar_pacientes(): Obtiene todos los pacientes
- guardar_paciente(): Guarda/actualiza un paciente
- cargar_historial_medico(): Obtiene historial de un paciente
- guardar_historial(): Añade un registro al historial
================================================================================
"""

import json
import os
import random

# Rutas a los archivos de datos
FILE_PACIENTES = "mobile_app/pacientes.json"
FILE_HISTORIAL = "mobile_app/historial_pacientes.json"


# =============================================================================
# FUNCIONES DE CARGA (Lectura de datos)
# =============================================================================

def cargar_json_seguro(filepath):
    """
    Carga un archivo JSON de forma segura.
    
    Maneja casos de:
    - Archivo no existe
    - Archivo vacío
    - JSON corrupto/malformado
    
    Args:
        filepath: Ruta al archivo JSON
        
    Returns:
        dict: Contenido del JSON o diccionario vacío si hay error
    """
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: 
                return {}  # Archivo vacío
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        print(f"⚠️ Alerta: El archivo {filepath} estaba corrupto. Se ha reiniciado.")
        return {}


def cargar_pacientes():
    """
    Carga la base de datos de pacientes.
    
    Returns:
        dict: Diccionario con todos los pacientes, indexados por ID
              Ej: {"P_1": {datos_paciente}, "P_2": {...}}
    """
    return cargar_json_seguro(FILE_PACIENTES)


def cargar_historial_medico(id_paciente):
    """
    Carga el historial médico de un paciente específico.
    
    Args:
        id_paciente: ID único del paciente (ej: "P_1")
        
    Returns:
        list: Lista de registros de visitas del paciente
              Lista vacía si el paciente no tiene historial
    """
    data = cargar_json_seguro(FILE_HISTORIAL)
    return data.get(id_paciente, [])


# =============================================================================
# FUNCIONES DE GUARDADO (Escritura de datos)
# =============================================================================

def guardar_paciente(paciente):
    """
    Guarda o actualiza un paciente en la base de datos.
    
    Si el paciente ya existe (mismo ID), se sobrescribe.
    Si es nuevo, se añade a la base de datos.
    
    Args:
        paciente: Diccionario con los datos del paciente
                 Debe incluir campo "id"
    """
    db = cargar_pacientes()
    db[paciente["id"]] = paciente
    with open(FILE_PACIENTES, "w", encoding="utf-8") as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)


def guardar_historial(id_paciente, registro):
    """
    Añade un registro al historial médico de un paciente.
    
    Si el paciente no tiene historial previo, se crea uno nuevo.
    
    Args:
        id_paciente: ID único del paciente
        registro: Diccionario con los datos de la visita
                 Debe incluir fecha, tipo, y datos clínicos
    """
    # Cargar historial actual de forma segura
    db = cargar_json_seguro(FILE_HISTORIAL)
    
    # Asegurar que existe la lista para este paciente
    if id_paciente not in db: 
        db[id_paciente] = []
        
    # Añadir el nuevo registro
    db[id_paciente].append(registro)
    
    # Guardar cambios
    with open(FILE_HISTORIAL, "w", encoding="utf-8") as f: 
        json.dump(db, f, indent=4, ensure_ascii=False)


# =============================================================================
# UTILIDADES
# =============================================================================

def generar_nhc_random():
    """
    Genera un Número de Historia Clínica aleatorio.
    
    Útil para asignar NHC a pacientes nuevos de forma automática.
    
    Returns:
        str: NHC de 6 dígitos (ej: "123456")
    """
    return str(random.randint(100000, 999999))


def borrar_paciente_db(id_paciente):
    """
    Elimina un paciente de la base de datos.
    
    NOTA: No elimina el historial médico asociado.
    
    Args:
        id_paciente: ID único del paciente a eliminar
    """
    db = cargar_pacientes()
    if id_paciente in db:
        del db[id_paciente]
        with open(FILE_PACIENTES, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
