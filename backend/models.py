"""
================================================================================
MODELS.PY - Modelos de Datos Pydantic
================================================================================

Este módulo define los esquemas de datos (modelos) que se usan en la API
para validar la estructura de las prescripciones médicas.

Pydantic se encarga de:
- Validar que los datos tienen el tipo correcto
- Proporcionar valores por defecto
- Generar documentación automática en Swagger/OpenAPI

MODELOS:
- Medicamento: Un medicamento individual de la receta
- PautaMedica: La receta completa con lista de medicamentos
================================================================================
"""

from pydantic import BaseModel
from typing import List, Optional


class Medicamento(BaseModel):
    """
    Representa un medicamento individual dentro de una receta.
    
    Atributos:
        nombre: Nombre del medicamento (ej: "Ibuprofeno")
        dosis: Cantidad por toma (ej: "400mg" o "10mg/kg")
        frecuencia: Intervalo entre dosis (ej: "Cada 8 horas")
        duracion: Tiempo total de tratamiento (opcional, ej: "5 días")
    
    Ejemplo:
        >>> med = Medicamento(
        ...     nombre="Ibuprofeno",
        ...     dosis="400mg",
        ...     frecuencia="Cada 8 horas",
        ...     duracion="5 días"
        ... )
    """
    nombre: str
    dosis: str
    frecuencia: str
    duracion: Optional[str] = None


class PautaMedica(BaseModel):
    """
    Representa una receta médica completa.
    
    Atributos:
        lista_medicamentos: Lista de Medicamento con todos los fármacos
        notas_adicionales: Instrucciones especiales (opcional)
    
    Ejemplo:
        >>> pauta = PautaMedica(
        ...     lista_medicamentos=[
        ...         Medicamento(nombre="Ibuprofeno", dosis="400mg", frecuencia="Cada 8h"),
        ...         Medicamento(nombre="Paracetamol", dosis="500mg", frecuencia="Cada 6h")
        ...     ],
        ...     notas_adicionales="Tomar con alimentos"
        ... )
    """
    lista_medicamentos: List[Medicamento]
    notas_adicionales: Optional[str] = None
