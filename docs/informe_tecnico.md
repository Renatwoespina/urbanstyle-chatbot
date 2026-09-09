# Informe Técnico: Chatbot de Atención al Cliente con Agentes LLM y RAG

**Proyecto:** UrbanStyle Chile - Sistema de Atención al Cliente Inteligente
**Asignatura:** ISY0101 - Ingeniería de Soluciones con IA
**Institución:** Duoc UC
**Equipo:** Renato Espina (21.801.161-6), Javier García (21.655.097-8) y Benjamín Rojas (21.796.829-1)
**Fecha:** Septiembre de 2026

---

## 1. Introducción

El presente informe documenta el diseño, implementación y evaluación de un chatbot inteligente para la atención al cliente de UrbanStyle Chile, una tienda de ropa y moda de tamaño mediano con presencia regional. La solución combina un modelo de lenguaje (LLM) con una técnica de Retrieval-Augmented Generation (RAG) para recuperar información relevante de fuentes internas y generar respuestas precisas y contextuales en tiempo real. El objetivo es reducir los tiempos de respuesta, automatizar consultas frecuentes y mejorar la experiencia del cliente.

## 2. Análisis del Caso Organizacional (IE1)

### 2.1 Descripción de la Organización

UrbanStyle Chile es una empresa del sector retail de moda, con aproximadamente 120 empleados y 8 tiendas distribuidas a nivel regional. La empresa opera tanto en tienda física como en una plataforma de comercio electrónico, lo que genera una demanda constante y variada de atención al cliente.

### 2.2 Problema Identificado

La organización enfrenta los siguientes desafíos operativos:

- **Tiempos de respuesta prolongados:** Las consultas por correo demoran entre 24 y 48 horas en ser atendidas.
- **Alta repetición de consultas:** Stock, tallas, precios y políticas de devolución son preguntas recurrentes y simples.
- **Abandono de carritos de compra:** La falta de información inmediata durante la compra online provoca que los clientes abandonen el proceso.
- **Sobrecarga del personal:** Los agentes humanos dedican gran parte de su tiempo a consultas repetitivas.

### 2.3 Objetivos de la Intervención

1. Reducir el tiempo de respuesta promedio de 24 horas a menos de 2 minutos.
2. Automatizar al menos el 70% de las consultas frecuentes.
3. Mejorar la experiencia de compra en la plataforma online.
4. Liberar tiempo del personal humano para atender consultas de mayor complejidad.

### 2.4 Fuentes de Datos Disponibles

| Fuente | Formato | Registros | Propósito |
|--------|---------|-----------|-----------|
| Catálogo de Productos | CSV | 15 productos | Precios, stock, tallas, colores |
| Preguntas Frecuentes | TXT | 15 preguntas | Horarios, envíos, pagos, cambios |
| Política de Devoluciones | TXT | 1 documento | Plazos, condiciones, procesos |
| Guía de Tallas | TXT | 1 documento | Tablas de tallas por categoría |

## 3. Diseño de la Solución (IE4)

### 3.1 Arquitectura del Sistema

La arquitectura propuesta se compone de los siguientes módulos:

1. **Capa de Entrada:** Interfaz de usuario en línea de comandos (CLI) para el cliente.
2. **Módulo de Recuperación:** Retriever local basado en TF-IDF que indexa y selecciona los documentos más relevantes.
3. **Módulo de Procesamiento:** Construcción del contexto a partir de los documentos recuperados y el prompt del sistema.
4. **Módulo de Generación:** Modelo de lenguaje LLM (GPT-OSS a través de Groq) que elabora la respuesta final.

### 3.2 Flujo del Sistema

```
Entrada del Usuario → Indexación TF-IDF de los documentos → Vectorización de la consulta
    → Cálculo de similitud y recuperación de top-K → Construcción del contexto
    → Generación de la Respuesta con el LLM → Salida al usuario
```

### 3.3 Diagrama de Arquitectura

```mermaid
graph TB
    A[Usuario] -->|Consulta| B[Retriever TF-IDF<br/>Local (scikit-learn)]
    B -->|Top 4 documentos| C[Construcción de<br/>Contexto]
    C -->|Contexto + Prompt| D[LLM<br/>GPT-OSS vía Groq]
    D -->|Respuesta| A

    subgraph "Fuentes de Datos Internas"
        F[Catálogo CSV]
        G[FAQ TXT]
        H[Política Devoluciones TXT]
        I[Guía de Tallas TXT]
    end

    F --> J[Indexación<br/>TF-IDF Local]
    G --> J
    H --> J
    I --> J
    J -->|Índice de vectores| B
```

## 4. Formulación de Prompts Optimizados (IE2)

### 4.1 Prompt del Sistema (System Prompt)

Se definió un prompt del sistema que establece el rol del asistente, sus restricciones y el tono de comunicación:

```
Eres UrbanBot, el asistente virtual oficial de UrbanStyle Chile, una tienda de ropa y moda.
Tu función es ayudar a los clientes con consultas sobre productos, stock, tallas, precios,
pedidos, envíos, cambios y devoluciones.

REGLAS IMPORTANTES:
- Responde SOLO con información que encuentres en el contexto proporcionado.
- Si no tienes información suficiente, indica amablemente que el cliente contacte soporte.
- Usa un tono amigable, profesional y empático.
- Nunca inventes información sobre precios, stock o políticas.
- Responde en español.
```

### 4.2 Plantilla de Contexto (Context Wrapper)

Los documentos recuperados se integran junto con la pregunta del usuario mediante la siguiente plantilla:

```
Contexto relevante de UrbanStyle:
{context}

Pregunta del cliente: {question}

Responde de forma clara, amable y usando solo la información del contexto. Si la información
no es suficiente, indica que el cliente debe contactar soporte directamente.
```

### 4.3 Justificación de los Prompts

Los prompts fueron diseñados siguiendo buenas prácticas de ingeniería de prompts:

- **Claridad:** Instrucciones explícitas sobre el comportamiento esperado del asistente.
- **Restricción al contexto:** Se limita el modelo a responder solo con la información recuperada, reduciendo el riesgo de alucinaciones.
- **Tono:** Se define un estilo empático y profesional acorde al sector retail.
- **Fallback:** Se establece un comportamiento controlado cuando no existe información suficiente.

## 5. Implementación del Pipeline RAG (IE3)

### 5.1 Carga y Procesamiento de Documentos

El módulo de carga reúne las cuatro fuentes de datos:

```python
def load_all_documents() -> list[Document]:
    all_docs = []
    all_docs.extend(load_catalog())        # Catálogo de productos
    all_docs.extend(split_documents(load_faq()))              # Preguntas frecuentes
    all_docs.extend(split_documents(load_policies()))         # Política de devoluciones
    all_docs.extend(split_documents(load_size_guide()))       # Guía de tallas
    return all_docs
```

### 5.2 Módulo de Recuperación (Retriever TF-IDF local)

El sistema utiliza un retriever basado en **TF-IDF** implementado con `scikit-learn`. Este enfoque:

- Indexa los documentos y los convierte en una matriz TF-IDF (términos y bigramas).
- Vectoriza la consulta del usuario con la misma representación.
- Calcula la similitud coseno entre la consulta y los documentos únicamente con álgebra matricial local.
- Selecciona los **top 4** documentos más relevantes (valor `k=4`).

La elección del retriever local evita depender de servicios externos de embeddings, reduciendo costos, latencia y requisitos de red, además de funcionar correctamente con contenido en español.

### 5.3 Construcción del Contexto

Los documentos recuperados se concatenan con separadores para formar el contexto que acompaña al prompt:

```python
context = "\n\n---\n\n".join(d.page_content for d in relevant)
prompt = SYSTEM_PROMPT + "\n\n" + CONTEXT_WRAPPER.format(context=context, question=question)
```

### 5.4 Módulo de Generación (LLM)

La respuesta es generada por el modelo **GPT-OSS (openai/gpt-oss-120b)** a través de la plataforma **Groq**, configurado con una temperatura de `0.3` para favorecer respuestas precisas y consistentes. El modelo combina el sistema, el contexto recuperado y la pregunta del usuario para elaborar la respuesta final.

> Nota: inicialmente se utilizó `qwen/qwen3.8-27b`, pero el plan gratuito de
> Groq limita sus tokens de salida por minuto (1000), lo que provocaba errores
> 429 en respuestas largas. Se migró a `openai/gpt-oss-120b`, que también está
> disponible en Groq y no presenta esa restricción.

## 6. Evaluación del Sistema (IE3 / IE6)

### 6.1 Pruebas Realizadas

Se realizaron pruebas funcionales del pipeline:

| Caso de Prueba | Resultado |
|----------------|-----------|
| Carga del catálogo (15 productos) | Exitoso |
| Carga de preguntas frecuentes (15) | Exitoso |
| Indexación TF-IDF de documentos | Exitoso |
| Consulta sobre precio de producto | Exitoso |
| Consulta sobre política de devolución | Exitoso |
| Consulta sobre horarios de atención | Exitoso |
| Consulta fuera del alcance de datos | Fallback correcto |

### 6.2 Ejemplo Real de Consulta

```
Tú: ¿Cuánto cuesta la polera Básica Clásica?
UrbanBot: La Polera Básica Clásica tiene un precio de $12.990.
Este producto está disponible en tallas S, M, L y XL, y en los colores Blanco, Negro y Azul.
[Fuentes: catalogo]
```

### 6.3 Métricas Cualitativas

- **Coherencia datos-respuesta:** Las respuestas se construyen a partir de los documentos recuperados, por lo que existe una trazabilidad directa entre la fuente y la respuesta.
- **Precisión:** Los hechos (precios, tallas, políticas) coinciden con el catálogo y las políticas cargadas.
- **Relevancia:** El retriever TF-IDF selecciona los documentos pertinentes a la consulta.
- **Fallback robusto:** Las consultas sin respaldo devuelven una respuesta controlada.

## 7. Decisiones de Diseño y Restricciones (IE5)

### 7.1 Selección de Tecnologías

| Decisión | Alternativas | Justificación |
|----------|--------------|---------------|
| LLM: GPT-OSS vía Groq | OpenAI, Gemini | API gratuita con plan generoso, sin necesidad de tarjeta de crédito |
| Retriever: TF-IDF local | Embeddings, ChromaDB | Ligero, sin dependencias externas, funciona con español, sin costo |
| Orquestación: Python puro (CLI) | LangChain | Menos dependencias, más simple de auditar y ejecutar en cualquier equipo |
| Modelo GPT-OSS 120B | Qwen, Llama | Buen desempeño en español, disponible en la cuenta de Groq y sin límites de tokens estrictos en el plan gratuito |

### 7.2 Restricciones y Limitaciones

- **Dependencia de red:** Se requiere conexión a internet para invocar la API de Groq.
- **Privacidad:** Las consultas son procesadas por el proveedor LLM (Groq).
- **Alcance de datos:** Las respuestas dependen de la calidad y actualización de los documentos cargados.
- **Sin estado multi-turno:** El chatbot responde consultas individuales sin memoria de largo plazo entre turnos.
- **Sin inventario en tiempo real:** El stock mostrado corresponde al catálogo estático cargado.

## 8. Conclusiones

El proyecto demuestra la viabilidad de implementar un sistema de atención al cliente basado en agentes LLM y RAG en el sector retail. Los principales logros son:

1. **Reducción del tiempo de respuesta:** De 24 horas a respuesta inmediata (menos de 2 minutos).
2. **Automatización efectiva:** Las consultas frecuentes se resuelven sin intervención humana.
3. **Arquitectura escalable:** Es posible incorporar nuevas fuentes de datos con mínimos cambios.
4. **Costo-eficiencia:** El uso de una API gratuita y un retriever local minimiza costos.

### Reflexión Individual

_Espacio reservado para la reflexión personal de cada integrante, redactada sin apoyo de IA, incluyendo el aprendizaje obtenido y la contribución individual al proyecto._

- **Renato Espina:**
  _[Redactar aquí, sin IA]_

- **Javier García:**
  _[Redactar aquí, sin IA]_

- **Benjamín Rojas:**
  _[Redactar aquí, sin IA]_

## 9. Referencias (Normativa APA)

- Groq. (2026). *GroqCloud - API documentation*. Recuperado de https://console.groq.com
- scikit-learn. (2026). *TF-IDF vectorizer*. Recuperado de https://scikit-learn.org
- Python Software Foundation. (2026). *Python 3.11 documentation*.
- American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7.ª ed.).
- Bibliotecas Duoc UC. (2025). *Guía de citación y referencias bajo norma APA*. Recuperado de https://bibliotecas.duoc.cl/ia

---

## Anexo A: Diagrama de Arquitectura

Se presenta en la sección 3.3 el diagrama Mermaid de la arquitectura, que identifica los componentes clave (retriever, construcción de contexto, LLM) y las fuentes de datos internas.

## Anexo B: Evidencia de Ejecución del Código

```
C:\...\urbanstyle-chatbot>python -m src.chatbot
============================================================
  URBANSTYLE CHILE - Chatbot de Atención al Cliente
  Escribe 'salir' para terminar la conversación
============================================================
Inicializando pipeline RAG...
[INFO] Documentos indexados: 24 chunks (retriever TF-IDF local)
Listo. Puedes hacer tu consulta.

Tú: ¿Cuánto cuesta la polera básica clásica?
UrbanBot: La Polera Básica Clásica tiene un precio de $12.990.
Este producto está disponible en tallas S, M, L y XL, y en los colores Blanco, Negro y Azul.
[Fuentes: catalogo]
```
