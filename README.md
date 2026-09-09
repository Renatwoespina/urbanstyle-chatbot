# UrbanStyle Chatbot - Atención al Cliente con RAG

Chatbot inteligente para atención al cliente de UrbanStyle Chile, basado en LLM y técnica RAG (Retrieval-Augmented Generation).

## Descripción

Sistema de atención al cliente que utiliza inteligencia artificial para responder consultas sobre productos, stock, tallas, precios, envíos, cambios y devoluciones. El sistema recupera información relevante de fuentes internas (catálogo, FAQ, políticas, guía de tallas) mediante un retriever local TF-IDF y genera respuestas contextuales con un modelo de lenguaje (GPT-OSS vía Groq).

## Arquitectura

```
+------------------+
|  Chatbot UrbanStyle        |
|  +-----------------+       |
|  |  Usuario (Input)|       |
|  +--------+--------+       |
|           |                |
|           v                |
|  +-----------------+       |
|  | Retriever TF-IDF|       |
|  |   local (k=4)   |       |
|  +--------+--------+       |
|           |                |
|           v                |
|  +-----------------+       |
|  | Construcción de |       |
|  |   Contexto      |       |
|  +--------+--------+       |
|           |                |
|           v                |
|  +-----------------+       |
|  |  LLM (GPT-OSS)  |       |
|  |   vía Groq      |       |
|  +--------+--------+       |
|           |                |
|           v                |
|  +-----------------+       |
|  |    Respuesta    |       |
|  +-----------------+       |
+------------------+
```

### Fuentes de Datos
- Catálogo de productos (CSV)
- Preguntas frecuentes (TXT)
- Política de devoluciones (TXT)
- Guía de tallas (TXT)

## Componentes

| Componente | Tecnología | Función |
|------------|-----------|---------|
| LLM | GPT-OSS (openai/gpt-oss-120b) vía Groq | Generación de respuestas |
| Retriever | TF-IDF local (scikit-learn) | Recuperación de documentos relevantes |
| Orquestación | Python puro (CLI) | Carga de documentos, construcción de contexto e integración con Groq |
| Datos | CSV + TXT | Catálogo, FAQ, políticas, tallas |

## Instalación

### Prerrequisitos
- Python 3.10+
- Cuenta en [GroqCloud](https://console.groq.com) con API key (gratuita, empieza con `gsk_`)

### Pasos

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/urbanstyle-chatbot.git
cd urbanstyle-chatbot
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env y agregar tu GROQ_API_KEY
```

## Uso

### Ejecutar el chatbot
```bash
python -m src.chatbot
```

### Ejemplo de conversación
```
Tú: ¿Cuánto cuesta la polera Básica Clásica?
UrbanBot: La Polera Básica Clásica tiene un precio de $12.990.
Este producto está disponible en tallas S, M, L y XL, y en los colores Blanco, Negro y Azul.
[Fuentes: catalogo]

Tú: ¿Puedo devolver un producto que compré hace 20 días?
UrbanBot: Sí, puedes realizar un cambio o devolución. Según nuestra política,
tienes hasta 30 días desde la fecha de recepción. El producto debe estar sin usar,
con etiquetas y en su empaque original.
[Fuentes: politica_devoluciones]
```

## Estructura del Proyecto

```
urbanstyle-chatbot/
├── data/
│   ├── catalogo_productos.csv    # Catálogo de productos
│   ├── faq.txt                   # Preguntas frecuentes
│   ├── guia_tallas.txt           # Guía de tallas
│   └── politica_devoluciones.txt # Política de cambios
├── src/
│   ├── __init__.py
│   ├── chatbot.py                # Interfaz principal
│   ├── load_documents.py         # Carga de documentos
│   ├── prompts.py                # Prompts optimizados
│   └── rag_pipeline.py           # Pipeline RAG
├── tests/
│   └── test_pipeline.py          # Pruebas unitarias
├── docs/
│   └── informe_tecnico.md        # Informe técnico (APA)
├── .env.example                  # Ejemplo de variables
├── GUIA_PASO_A_PASO.md           # Guía de instalación detallada
├── README.md                     # Esta documentación
└── requirements.txt              # Dependencias
```

## Documentos Incluidos

- **Catálogo de productos**: 15 productos con SKU, precio, stock, tallas y descripción
- **FAQ**: 15 preguntas frecuentes sobre horarios, envíos, pagos y cambios
- **Política de devoluciones**: Documento completo con plazos, condiciones y procesos
- **Guía de tallas**: Tablas de tallas para hombres, mujeres y unisex

## Consideraciones Técnicas

- **Recuperación**: Retriever TF-IDF local con scikit-learn, selecciona los top 4 documentos más relevantes.
- **LLM**: Modelo GPT-OSS (openai/gpt-oss-120b) a través de la API de Groq, con temperatura 0.3.
- **Idioma**: Soporte nativo para consultas en español.
- **Sin dependencias externas de embeddings**: Todo el proceso de recuperación es local y sin costo.

## Licencia

Proyecto académico - Ingeniería de Soluciones con IA (ISY0101)