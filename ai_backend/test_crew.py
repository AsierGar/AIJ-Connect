import sys
import os

# Esto ayuda a que el código encuentre tus carpetas nuevas
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agents.tripulacion import ejecutar_validacion_medica

print("--- 🤖 INICIANDO SISTEMA DE IA ---")

# Simulamos que el médico dicta esto:
TEXTO_DICTADO = "Prescribo Metotrexato 15 mg semanal y acido folico."
PESO_PACIENTE = 25.0
ID_PACIENTE = "PACIENTE_PRUEBA"

try:
    print(f"🎤 Analizando: '{TEXTO_DICTADO}'")
    resultado = ejecutar_validacion_medica(TEXTO_DICTADO, PESO_PACIENTE, ID_PACIENTE)
    print("\n✅ ¡ÉXITO! La IA ha respondido:")
    print(resultado)
except Exception as e:
    print(f"\n❌ Error: {e}")