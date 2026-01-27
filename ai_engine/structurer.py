"""
================================================================================
STRUCTURER.PY - Agentes de Extracción y Cálculo de Dosis
================================================================================

Este módulo implementa dos agentes que trabajan en equipo:

1. AgenteEstructurador (IA): Extrae información del texto médico usando Llama3
2. AgenteMatematico (Python): Calcula las dosis exactas sin errores de IA

ARQUITECTURA "DIVIDE Y VENCERÁS":
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Texto Médico   │────▶│  Agente IA      │────▶│  Agente        │
│  "Ibuprofeno    │     │  (extracción)   │     │  Matemático    │
│   10mg/kg..."   │     └─────────────────┘     │  (cálculo)     │
└─────────────────┘                              └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  JSON Final     │
                                               │  con dosis      │
                                               │  calculadas     │
                                               └─────────────────┘

¿POR QUÉ DOS AGENTES?
Los LLMs son malos en matemáticas. Pueden confundir 10mg/kg * 25kg y dar
resultados incorrectos. Por eso separamos:
- IA: Solo extrae texto (su punto fuerte)
- Python: Solo calcula (matemáticas perfectas)
================================================================================
"""

from langchain_community.llms import Ollama
import json
import re


class AgenteMatematico:
    """
    Agente de cálculo matemático puro (sin IA).
    
    Este agente NO "piensa", solo aplica matemáticas rígidas e infalibles.
    Busca dosis en formato mg/kg y las multiplica por el peso del paciente.
    
    EJEMPLO:
        Entrada: "10 mg/kg" + peso=25kg
        Salida: "250 mg"
    """
    
    def calcular_dosis_exactas(self, pauta_json: dict, peso_paciente: float) -> dict:
        """
        Recibe la estructura extraída por la IA y calcula las dosis reales.
        
        Args:
            pauta_json: Diccionario con tratamiento_secuencial extraído por la IA
            peso_paciente: Peso del paciente en kg
            
        Returns:
            dict: El mismo JSON pero con campos adicionales:
                - dosis_calculada: "250 mg"
                - explicacion_calculo: "10 mg/kg x 25 kg"
        """
        print(f"\n🧮 AGENTE MATEMÁTICO ACTIVADO (Peso: {peso_paciente} kg)")
        
        # Si no hay peso válido, no podemos calcular
        if not peso_paciente or peso_paciente <= 0:
            print("   ⚠️ No hay peso, omitiendo cálculo.")
            return pauta_json

        lista_medicamentos = pauta_json.get("tratamiento_secuencial", [])
        
        for item in lista_medicamentos:
            dosis_texto = str(item.get("dosis", "")).lower()
            nombre = item.get("nombre", "Fármaco")
            
            # =================================================================
            # DETECCIÓN DE DOSIS POR PESO
            # =================================================================
            # Regex que busca: número + mg + / o "por" + kg
            # Ejemplos que detecta: "10mg/kg", "10 mg / kg", "10 mg por kg"
            match = re.search(r"(\d+([.,]\d+)?)\s*mg\s*[/|por]\s*kg", dosis_texto)
            
            if match:
                try:
                    # 1. Extraer el número (maneja tanto "10" como "10,5")
                    numero_str = match.group(1).replace(",", ".")
                    dosis_por_kg = float(numero_str)
                    
                    # 2. MULTIPLICACIÓN EXACTA (aquí no hay errores de IA)
                    total_mg = dosis_por_kg * peso_paciente
                    
                    # 3. Formatear bonito (sin decimales innecesarios)
                    if total_mg.is_integer():
                        total_final = f"{int(total_mg)} mg"
                    else:
                        total_final = f"{total_mg:.1f} mg"
                    
                    print(f"   ✅ CÁLCULO: {nombre} -> {dosis_por_kg} mg/kg * {peso_paciente} kg = {total_final}")
                    
                    # 4. Añadir campos calculados al JSON
                    item["dosis_calculada"] = total_final
                    item["explicacion_calculo"] = f"{dosis_por_kg} mg/kg x {peso_paciente} kg"
                    
                except Exception as e:
                    print(f"   ❌ Error matemático interno: {e}")
            else:
                # Si la dosis es fija (ej: "500mg"), no hay que calcular
                print(f"   ℹ️ '{nombre}' tiene dosis fija ({dosis_texto}), no requiere cálculo.")
                if "dosis_calculada" not in item:
                    item["dosis_calculada"] = item.get("dosis")

        # Devolver JSON enriquecido con las matemáticas
        pauta_json["tratamiento_secuencial"] = lista_medicamentos
        return pauta_json


class AgenteEstructurador:
    """
    Agente de IA que extrae información estructurada del texto médico.
    
    Usa Llama3 para "leer" el texto del médico y convertirlo en JSON.
    NO hace cálculos matemáticos - eso lo delega al AgenteMatematico.
    
    Atributos:
        llm: Modelo Ollama (Llama3) para procesamiento de lenguaje
        matematico: Instancia de AgenteMatematico para cálculos
    """
    
    def __init__(self):
        """Inicializa el agente con Llama3 y el matemático."""
        self.llm = Ollama(model="llama3", temperature=0)
        self.matematico = AgenteMatematico()
    
    def estructurar_texto(self, texto_medico: str, peso_kg: float = 0.0) -> dict:
        """
        Extrae información del texto médico y calcula dosis.
        
        Args:
            texto_medico: Texto libre con la prescripción
                         Ej: "Ibuprofeno 10mg/kg cada 8h durante 5 días"
            peso_kg: Peso del paciente en kg (para calcular dosis)
            
        Returns:
            dict: Estructura con el tratamiento:
                {
                    "tratamiento_secuencial": [
                        {
                            "nombre": "Ibuprofeno",
                            "dosis": "10mg/kg",
                            "dosis_calculada": "300 mg",  # Si peso=30kg
                            "frecuencia_horas": 8,
                            "duracion_dias": 5,
                            "instruccion_texto": "cada 8 horas durante 5 días"
                        }
                    ]
                }
        """
        # =================================================================
        # PASO 1: EXTRACCIÓN CON IA
        # =================================================================
        # El prompt indica explícitamente que NO calcule nada,
        # solo extraiga el texto tal cual
        prompt = f"""
        Eres un asistente administrativo médico.
        TEXTO: "{texto_medico}"
        
        Extrae los datos en este JSON exacto.
        IMPORTANTE: En "dosis", escribe EXACTAMENTE lo que dice el médico (ej: "10mg/kg").
        NO intentes calcular nada.
        
        {{
            "tratamiento_secuencial": [
                {{
                    "nombre": "Nombre del fármaco",
                    "dosis": "10mg/kg", 
                    "frecuencia_horas": 8,
                    "duracion_dias": 5,
                    "instruccion_texto": "cada 8 horas..."
                }}
            ]
        }}
        Devuelve SOLO el JSON.
        """
        
        try:
            print("\n🤖 AGENTE IA: Leyendo texto...")
            respuesta = self.llm.invoke(prompt)
            
            # Limpiar y extraer el JSON de la respuesta
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}') + 1
            json_str = respuesta[inicio:fin]
            datos_ia = json.loads(json_str)
            
            # =================================================================
            # PASO 2: CÁLCULO CON MATEMÁTICO
            # =================================================================
            # Delegamos las matemáticas al agente especializado
            datos_finales = self.matematico.calcular_dosis_exactas(datos_ia, peso_kg)
            
            return datos_finales
            
        except Exception as e:
            print(f"❌ Error en Agente IA: {e}")
            return {"tratamiento_secuencial": [], "error": str(e)}
