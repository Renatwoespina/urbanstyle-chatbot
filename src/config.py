"""Configuración central del agente UrbanStyle 2.0.

Agrupa rutas, parámetros de memoria, de planificación y de ejecución del agente
para que todos los módulos lean la misma fuente de verdad.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
SCRIPTS_DIR = BASE_DIR / "scripts"

CATALOGO_CSV = DATA_DIR / "catalogo_productos.csv"
FAQ_TXT = DATA_DIR / "faq.txt"
POLITICA_TXT = DATA_DIR / "politica_devoluciones.txt"
TALLAS_TXT = DATA_DIR / "guia_tallas.txt"

MEMORIA_FILE = DATA_DIR / "memoria.json"
SOLICITUDES_FILE = DATA_DIR / "solicitudes.json"
PLAN_FILE = DATA_DIR / "plan_actual.json"

MODEL = os.getenv("URBAN_MODEL", "openai/gpt-oss-120b")
TEMPERATURE = float(os.getenv("URBAN_TEMPERATURE", "0"))
MAX_TOKENS = int(os.getenv("URBAN_MAX_TOKENS", "1200"))
MAX_REINTENTOS_LLM = int(os.getenv("URBAN_MAX_RETRIES", "5"))
REASONING_EFFORT = os.getenv("URBAN_REASONING_EFFORT", "low")

# --- Memoria ---
VENTANA_CORTO_PLAZO = int(os.getenv("URBAN_VENTANA", "8"))
TURNO_PARA_RESUMEN = int(os.getenv("URBAN_RESUMEN_EN", "12"))
MAX_RESUMENES = 3
RECUPERACION_SEMANTICA_K = 4

# --- Recuperación RAG ---
TOP_K_RAG = 5

# --- Planificación ---
MAX_PASOS_PLAN = 5
MIN_PASOS_PLAN = 3

# --- Agente ---
MAX_ITERACIONES = 16
MAX_PASOS_EJECUCION = 6

_VARIABLES_ENTORNO = {
    "MODEL": ("URBAN_MODEL", str),
    "TEMPERATURE": ("URBAN_TEMPERATURE", float),
    "MAX_TOKENS": ("URBAN_MAX_TOKENS", int),
    "MAX_REINTENTOS_LLM": ("URBAN_MAX_RETRIES", int),
    "REASONING_EFFORT": ("URBAN_REASONING_EFFORT", str),
    "VENTANA_CORTO_PLAZO": ("URBAN_VENTANA", int),
    "TURNO_PARA_RESUMEN": ("URBAN_RESUMEN_EN", int),
}


def cargar_entorno() -> None:
    """Carga el .env una sola vez y refresca las variables configurables.

    Los valores del archivo tienen prioridad sobre los del proceso, de modo que
    `URBAN_MODEL` permite cambiar el modelo sin editar código (p. ej. para la
    demo en vivo si el modelo principal alcanza su cuota diaria).
    """
    load_dotenv(BASE_DIR / ".env", override=True)
    for nombre, (clave, convertir) in _VARIABLES_ENTORNO.items():
        valor = os.getenv(clave)
        if valor is None or not valor.strip():
            continue
        globals()[nombre] = convertir(valor)


def asegurar_directorios() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
