# 🏥 AIJ-Connect

**Plataforma de Reumatología Pediátrica con IA Generativa**

Sistema integral para el seguimiento de pacientes con Artritis Idiopática Juvenil (AIJ), que incorpora validación inteligente de prescripciones médicas mediante RAG (Retrieval Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![Ollama](https://img.shields.io/badge/LLM-Ollama%2FLlama3-green)

---

## 📋 Descripción

AIJ-Connect es una aplicación diseñada para reumatólogos pediátricos que permite:

- **Gestión de pacientes**: Alta, seguimiento y dashboard clínico completo
- **Registro de visitas**: Formulario con exploración articular interactiva (homúnculo)
- **Validación IA de prescripciones**: Sistema RAG que consulta guías médicas y fichas técnicas para validar dosis y detectar contraindicaciones
- **Portal del paciente**: Calendario de medicación y chatbot de ayuda
- **Cálculo automático**: JADAS-27, BSA, percentiles de crecimiento OMS

---

## 🎯 Problema que Resuelve

Los errores de dosificación en medicamentos de alto riesgo (como Metotrexato) son una preocupación crítica en reumatología pediátrica. AIJ-Connect:

1. **Valida automáticamente** las prescripciones contra guías clínicas indexadas
2. **Alerta al médico** si la dosis excede los límites recomendados
3. **Documenta la evidencia** utilizada para cada decisión
4. **Facilita el seguimiento** con dashboards visuales y métricas clínicas

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| **Frontend** | Streamlit |
| **Backend IA** | CrewAI + LangChain |
| **LLM** | Ollama (Llama3) - Local |
| **Embeddings** | nomic-embed-text / all-MiniLM-L6-v2 |
| **Vector Store** | ChromaDB / FAISS |
| **PDF Processing** | PyPDF, ReportLab |

---

## 📁 Estructura del Proyecto

```
AIJ-Connect/
├── mobile_app/              # Aplicación Streamlit principal
│   ├── app.py               # Punto de entrada
│   ├── ui_dashboard.py      # Dashboard clínico del paciente
│   ├── ui_visita.py         # Formulario de nuevas visitas
│   ├── ui_alta.py           # Alta de nuevos pacientes
│   ├── ui_patient.py        # Portal del paciente (calendario + chat)
│   ├── patient_bot.py       # Chatbot asistente para pacientes
│   ├── rag_engine.py        # Motor RAG para el chatbot
│   ├── homunculo_visita.py  # Homúnculo interactivo
│   ├── homunculo_dashboard.py # Heatmap de afectación articular
│   ├── auth.py              # Sistema de autenticación
│   ├── data_manager.py      # Gestión de persistencia JSON
│   └── styles.py            # Estilos CSS personalizados
│
├── ai_backend/              # Sistema de validación con IA
│   ├── agents/
│   │   ├── tripulacion.py   # Validación médica con RAG
│   │   └── run_tripulacion.py # Ejecutor CLI alternativo
│   ├── tools/
│   │   └── mis_herramientas.py # Tools RAG y procesamiento
│   └── ingest_knowledge.py  # Indexador de PDFs
│
├── ai_engine/               # Motor IA alternativo (Ollama directo)
│   ├── auditor.py           # Agente auditor de seguridad
│   ├── structurer.py        # Agente estructurador + matemático
│   └── ingest.py            # Indexador con Ollama embeddings
│
├── backend/                 # API REST (FastAPI)
│   ├── main.py              # Endpoints de la API
│   └── models.py            # Modelos Pydantic
│
└── data/                    # Guías médicas y fichas técnicas (PDFs)
```

---

## 🚀 Instalación

### Requisitos previos
- Python 3.11+
- [Ollama](https://ollama.ai/) instalado y corriendo

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/AsierGar/AIJ-Connect.git
cd AIJ-Connect

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelos de Ollama
ollama pull llama3
ollama pull nomic-embed-text

# 5. Indexar documentos médicos (solo primera vez)
python ai_backend/ingest_knowledge.py

# 6. Ejecutar aplicación
streamlit run mobile_app/app.py
```

### Credenciales por defecto
- **Usuario:** admin
- **Contraseña:** admin

---

## 📸 Características Principales

### 🏠 Dashboard Global
Vista general de todos los pacientes con métricas agregadas y filtros.

### 📊 Dashboard del Paciente
- Evolución temporal del JADAS
- Gráficos de peso vs percentiles OMS
- Heatmap de afectación articular histórica
- Historial completo de visitas

### 🩺 Nueva Visita
- Homúnculo interactivo para marcar articulaciones
- Escalas clínicas (EVA médico/paciente)
- Validación IA del plan de tratamiento
- Adjuntar documentos (analíticas, informes)

### 🤖 Validación IA
El sistema analiza el plan de tratamiento:
- Extrae fármaco, dosis y frecuencia
- Consulta guías médicas indexadas (RAG)
- Compara con dosis máximas permitidas
- Emite decisión: ✅ APROBADA | ⚠️ ALERTA | ❌ RECHAZADA

### 👶 Portal del Paciente
- Calendario con medicación programada
- Chatbot para resolver dudas
- Galería de fotos clínicas


---

## 👨‍💻 Autor

**Asier García**

Proyecto Capstone - Instituto de Inteligencia Artificial (IIA)  
Enero 2026

---

## 📄 Licencia

Este proyecto es parte de un trabajo académico. Uso educativo.

