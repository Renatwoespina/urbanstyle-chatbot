# GUÍA PASO A PASO - Chatbot UrbanStyle

Guía para instalar y ejecutar el chatbot UrbanStyle desde cero (Windows o Mac).

> Este proyecto usa **Groq** (API gratuita) como proveedor del modelo de
> lenguaje y un **retriever TF-IDF local** (scikit-learn) para la recuperación
> de documentos. No requiere OpenAI ni ChromaDB.

---

## PASO 1: OBTENER API KEY DE GROQ

### 1.1 Crear cuenta en Groq

1. Ve a: https://console.groq.com
2. Haz clic en **"Login"** o **"Sign Up"**.
3. Puedes registrarte con tu cuenta de Google o con email.
4. Completa el registro (te pedirá un correo y/o verificación).

### 1.2 Obtener la API Key

1. Una vez dentro, ve a: https://console.groq.com/keys
2. Haz clic en **"Create API Key"**.
3. Ponle un nombre (ej: "chatbot-urbanstyle").
4. Haz clic en **"Create"**.
5. **COPIA LA CLAVE INMEDIATAMENTE** (empieza con `gsk_...`, solo se muestra una vez).

### 1.3 Importante sobre costos

- Groq ofrece una **cuenta gratuita** con cuota de uso (rate limits) amplia.
- **No requiere tarjeta de crédito**.
- Cada consulta consume tokens de la cuota gratuita diaria, suficiente para
  desarrollo y evaluación del proyecto (IE5).

---

## PASO 2: ABRIR TERMINAL

### Windows:
1. Presiona las teclas **Windows + R**.
2. Escribe `cmd` y presiona Enter.
3. Se abre la ventana de comandos.

Alternativa: en el **Explorador de archivos**, ve a la carpeta del proyecto,
borra la barra de direcciones, escribe `cmd` y presiona Enter (abre la terminal
directamente en esa carpeta).

### Mac:
1. Presiona **Command + Espacio**.
2. Escribe "Terminal" y presiona Enter.

---

## PASO 3: UBICAR EL PROYECTO

Navega hasta la carpeta del proyecto:

**Windows:**
```
cd C:\ruta\a\urbanstyle-chatbot
```

**Mac:**
```
cd /ruta/a/urbanstyle-chatbot
```

Verifica que estás dentro viendo el contenido:

**Windows:**
```
dir
```

**Mac:**
```
ls
```

Debes ver las carpetas: `data`, `src`, `tests`, `docs` y los archivos
`requirements.txt`, `.env`, `README.md`.

---

## PASO 4: CREAR ENTORNO VIRTUAL (opcional pero recomendado)

### 4.1 Crear el entorno virtual

**Windows:**
```
python -m venv venv
```

**Mac:**
```
python3 -m venv venv
```

Si da error "python no reconocido", prueba:
```
py -m venv venv
```

### 4.2 Activar el entorno virtual

**Windows:**
```
venv\Scripts\activate
```

**Mac:**
```
source venv/bin/activate
```

Si funcionó, verás `(venv)` al inicio de la línea de comandos.

### 4.3 Verificar la versión de Python

```
python --version
```

Debe mostrar algo como `Python 3.10.x` o superior
(probado con Python 3.11.9).

---

## PASO 5: INSTALAR DEPENDENCIAS

El archivo `requirements.txt` ya existe con las dependencias correctas:
- `groq==0.37.1` — cliente de la API de Groq
- `python-dotenv==1.0.1` — lectura de la API key desde `.env`
- `scikit-learn==1.9.0` — retriever TF-IDF

Instala todo con:

**Windows:**
```
pip install -r requirements.txt
```

**Mac:**
```
pip3 install -r requirements.txt
```

> Opcional: si quieres ejecutar los tests además instala:
> ```
> pip install pytest
> ```

---

## PASO 6: CONFIGURAR LA API KEY

### 6.1 Copiar la plantilla

El proyecto incluye un archivo `.env.example`. Cópialo a `.env`:

**Windows:**
```
copy .env.example .env
```

**Mac:**
```
cp .env.example .env
```

### 6.2 Editar el archivo .env

Reemplaza el valor `tu_clave_aqui` por tu API key real de Groq.

**Usando Notepad (Windows):**
```
notepad .env
```

**Usando nano (Mac):**
```
nano .env
```

Guarda:
- Notepad: Ctrl+S y cierra.
- nano: Ctrl+X, presiona Y, Enter.

Verifica que el archivo tenga el formato:
```
GROQ_API_KEY=gsk_tu_clave_real
```

> ⚠️ **Seguridad:** el `.env` contiene tu clave y **no debe subirse a GitHub**
> ni compartirse. El archivo `.gitignore` lo excluye automáticamente.

---

## PASO 7: EJECUTAR LOS TESTS (opcional)

Desde la carpeta del proyecto:

**Windows / Mac:**
```
python -m pytest tests -v
```

Deberías ver: **65 pruebas aprobadas** (memoria, herramientas, planificador,
orquestación, recuperación y pipeline). No consumen cuota de Groq porque usan un
modelo simulado.

---

## PASO 8: EJECUTAR EL CHATBOT

**Windows:**
```
python -m src.chatbot
```

**Mac:**
```
python3 -m src.chatbot
```

Deberías ver:
```
============================================================
  URBANSTYLE CHILE - Chatbot de Atención al Cliente
  Escribe 'salir' para terminar la conversación
============================================================
Inicializando pipeline RAG...
[INFO] Documentos indexados: 48 chunks (retriever TF-IDF local)
Listo. Puedes hacer tu consulta.
```

Prueba escribir:
- "¿Cuánto cuesta la polera básica clásica?"
- "¿Quiero devolver el SKU URB-002 que compré hace 12 días"
- "Recibí el SKU URB-005 hace 60 días y tiene un defecto de fabricación"
- "¿Recuerdas el caso que abrí la vez pasada?"

Comandos disponibles dentro del chatbot: `/plan`, `/memoria`, `/estado`,
`/reset`, `/ayuda` y `salir`.

Para salir escribe: `salir`

---

## PASO 9: DEMO CON EVIDENCIA (Evaluación Parcial 2)

Ejecuta los 5 escenarios del caso organizacional y genera la evidencia en
`docs/evidencia_pruebas.txt` y `docs/evidencia_demo.json`:

```
python -m scripts.demo_caso --limpio
```

Variantes útiles:

```
python -m scripts.demo_caso -e 2        # sólo un escenario (defensa en vivo)
python -m scripts.demo_caso -e 1,2      # un rango de escenarios
python -m scripts.demo_caso --limpio --acumular   # conserva evidencia previa
python -m scripts.demo_caso --sin-supervision      # sin reflexión del supervisor
```

Si la cuota diaria de Groq se agota a mitad de la corrida, vuelve a lanzar el
mismo comando **sin `--limpio`** y con `--acumular`, indicando sólo los
escenarios que faltan (p. ej. `python -m scripts.demo_caso -e 3,4,5 --acumular`):
se conserva la evidencia previa y el estado de los escenarios que ya salieron
bien (memoria y folios), que es lo que necesita el escenario 5.

---

## PASO 10: REGENERAR LOS ENTREGABLES DE EP2

```
python -m scripts.generar_diagramas   # docs/diagrama_*.png
python -m scripts.generar_informe     # docs/Informe_EP2_UrbanStyle.docx
```

Antes de la defensa, revisa que el informe tenga **máximo 5 páginas** y completa
la sección **6.1 Reflexiones individuales** (se redactan a mano, sin IA).

---

## SOLUCIÓN DE ERRORES COMUNES

### Error: "python no se reconoce"
**Solución:** Instala Python desde https://www.python.org/downloads/ y marca la
casilla **"Add Python to PATH"** durante la instalación. Reinicia la terminal.

### Error: "pip no se reconoce"
**Solución:** Reinicia la terminal después de instalar Python, o usa
`python -m pip` en su lugar.

### Error: "No such file or directory"
**Solución:** Verifica que estás en la carpeta correcta del proyecto (`cd` o
`pwd`).

### Error: "GROQ_API_KEY not set"/"The api_key client option must be set"
**Solución:** Verifica que el archivo `.env` existe y tiene tu API key de Groq
en el formato `GROQ_API_KEY=gsk_...`. Asegúrate de ejecutar desde la carpeta
del proyecto.

### Error: "ModuleNotFoundError"
**Solución:** Asegúrate de que el entorno virtual está activado y de haber
ejecutado `pip install -r requirements.txt`.

### Error: modelo no disponible
**Solución:** El proyecto usa por defecto `openai/gpt-oss-120b`. Cambia la
variable `URBAN_MODEL` en el archivo `.env` por otro modelo disponible en tu
cuenta (por ejemplo `openai/gpt-oss-20b`) y vuelve a ejecutar.

### Error: "Rate limit reached ... (TPD)"
**Solución:** Es la cuota diaria gratuita de Groq (200 000 tokens por modelo).
Espera el tiempo que indica el propio mensaje y vuelve a intentar; si estabas
corriendo la demo, repítela con `--acumular` para no rehacer los escenarios que
ya salieron bien. También puedes cambiar `URBAN_MODEL` en `.env` a otro modelo:
la orquestación no cambia.