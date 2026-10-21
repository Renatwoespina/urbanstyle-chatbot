"""Genera los diagramas del informe (PNG de alta resolución) con matplotlib.

Salida en docs/:
    diagrama_arquitectura.png  -> orquestación de componentes
    diagrama_decision.png      -> planificación y decisión adaptativa
    diagrama_memoria.png       -> memoria de corto/largo plazo y recuperación

Uso:
    python -m scripts.generar_diagramas
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from src import config

AZUL = "#1f3b57"
AZUL_CLARO = "#dbe7f3"
TEAL = "#0f766e"
TEAL_CLARO = "#d7f0ed"
NARANJA = "#b45309"
NARANJA_CLARO = "#fdebd3"
GRIS = "#e5e7eb"
GRIS_TEXTO = "#374151"
ROJO = "#b91c1c"
ROJO_CLARO = "#fde2e1"


def caja(ax, x, y, w, h, texto, color=AZUL_CLARO, borde=AZUL, tam=9, peso="normal", radio=0.02):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle=f"round,pad=0.006,rounding_size={radio}",
            linewidth=1.2,
            edgecolor=borde,
            facecolor=color,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        texto,
        ha="center",
        va="center",
        fontsize=tam,
        color=GRIS_TEXTO,
        fontweight=peso,
        linespacing=1.35,
    )


def flecha(ax, x1, y1, x2, y2, color=AZUL, estilo="-|>", curvatura=0.0, grosor=1.4, etiqueta="", tam=8):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle=estilo,
            mutation_scale=13,
            linewidth=grosor,
            color=color,
            connectionstyle=f"arc3,rad={curvatura}",
            shrinkA=2,
            shrinkB=2,
        )
    )
    if etiqueta:
        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2 + 0.018,
            etiqueta,
            ha="center",
            va="bottom",
            fontsize=tam,
            color=color,
            style="italic",
        )


def _lienzo(titulo: str, ancho=12, alto=7):
    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(titulo, fontsize=13, fontweight="bold", color=AZUL, pad=12)
    return fig, ax


def diagrama_arquitectura() -> None:
    fig, ax = _lienzo("Arquitectura y orquestación del agente UrbanStyle 2.0")

    caja(ax, 0.34, 0.90, 0.32, 0.07, "Cliente / evaluador", GRIS, AZUL, 10, "bold")
    caja(ax, 0.30, 0.79, 0.40, 0.075, "Interfaz: src/chatbot.py  ·  scripts/demo_caso.py", GRIS, AZUL, 9)
    flecha(ax, 0.50, 0.898, 0.50, 0.868)

    caja(
        ax,
        0.27,
        0.60,
        0.46,
        0.155,
        "AgenteUrbanStyle  (LangChain AgentExecutor)\n"
        "create_tool_calling_agent + ChatGroq (GPT-OSS vía Groq)\n"
        "max_iterations=16 · reintento atómico",
        AZUL_CLARO,
        AZUL,
        9,
        "bold",
    )
    flecha(ax, 0.50, 0.788, 0.50, 0.758)

    caja(
        ax,
        0.02,
        0.61,
        0.21,
        0.13,
        "GestorMemoria\n· corto plazo (ventana 8)\n· compresión por resumen\n· largo plazo JSON",
        TEAL_CLARO,
        TEAL,
        8.5,
    )
    caja(
        ax,
        0.77,
        0.61,
        0.21,
        0.13,
        "Planificador\n· plan priorizado v1..vn\n· progreso por paso\n· replanificación",
        NARANJA_CLARO,
        NARANJA,
        8.5,
    )
    flecha(ax, 0.23, 0.675, 0.27, 0.675, TEAL, "<|-|>")
    flecha(ax, 0.73, 0.675, 0.77, 0.675, NARANJA, "<|-|>")

    ax.text(0.50, 0.555, "13 herramientas (StructuredTool · tags por familia)", ha="center", fontsize=9, color=AZUL, fontweight="bold")
    flecha(ax, 0.50, 0.598, 0.50, 0.573)

    caja(
        ax,
        0.02,
        0.38,
        0.30,
        0.155,
        "CONSULTA (4)\nbuscar_conocimiento\nconsultar_producto\nconsultar_stock\nconsultar_politica",
        GRIS,
        AZUL,
        8.2,
    )
    caja(
        ax,
        0.35,
        0.38,
        0.30,
        0.155,
        "ESCRITURA (3)\nregistrar_solicitud_devolucion\nregistrar_nota_caso\nguardar_en_memoria",
        GRIS,
        AZUL,
        8.2,
    )
    caja(
        ax,
        0.68,
        0.38,
        0.30,
        0.155,
        "RAZONAMIENTO (6)\nevaluar_devolucion · calcular\nplanificar · consultar_plan\nactualizar_plan · replanificar_plan",
        GRIS,
        AZUL,
        8.2,
    )
    for x in (0.17, 0.50, 0.83):
        flecha(ax, 0.50 if x == 0.50 else (0.42 if x < 0.5 else 0.58), 0.555, x, 0.537, AZUL, "<|-|>", grosor=1.1)

    caja(ax, 0.02, 0.17, 0.30, 0.13, "Corpus TF-IDF\nfaq · política · guía de tallas\n+ catálogo CSV", GRIS, AZUL, 8.5)
    caja(ax, 0.35, 0.17, 0.30, 0.13, "Persistencia JSON\ndata/solicitudes.json\ndata/memoria.json · plan_actual.json", GRIS, AZUL, 8.5)
    caja(ax, 0.68, 0.17, 0.30, 0.13, "LLM + política\nGroq API (familia GPT-OSS)\nmotor de reglas de devolución", GRIS, AZUL, 8.5)
    for x in (0.17, 0.50, 0.83):
        flecha(ax, x, 0.378, x, 0.302, AZUL, "<|-|>", grosor=1.1)

    ax.text(
        0.5,
        0.09,
        "Caché de evidencias por turno: evita repetir consultas deterministas al replanificar.",
        ha="center",
        fontsize=8.5,
        color=GRIS_TEXTO,
        style="italic",
    )
    fig.savefig(config.DOCS_DIR / "diagrama_arquitectura.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def diagrama_decision() -> None:
    fig, ax = _lienzo("Planificación y decisión adaptativa (replanificación)", 12.5, 6.4)

    caja(ax, 0.01, 0.52, 0.13, 0.12, "Solicitud\ndel cliente", GRIS, AZUL, 8.5, "bold")
    caja(ax, 0.17, 0.52, 0.14, 0.12, "planificar\n(objetivo, contexto)", AZUL_CLARO, AZUL, 8.5)
    caja(ax, 0.34, 0.52, 0.15, 0.12, "Evidencia\nconsulta + política\n+ stock", GRIS, AZUL, 8.5)
    caja(ax, 0.52, 0.52, 0.15, 0.12, "evaluar_devolucion\n(motor de reglas)", NARANJA_CLARO, NARANJA, 8.5)
    caja(ax, 0.70, 0.52, 0.12, 0.12, "¿Señal\nadaptativa?", ROJO_CLARO, ROJO, 8.5, "bold")

    for x1, x2 in ((0.14, 0.17), (0.31, 0.34), (0.49, 0.52), (0.67, 0.70)):
        flecha(ax, x1, 0.58, x2, 0.58)

    caja(
        ax,
        0.85,
        0.52,
        0.14,
        0.30,
        "SIN_CAMBIO\n\nregistrar_solicitud\n_devolucion → folio\n\nrespuesta + folio",
        TEAL_CLARO,
        TEAL,
        8.2,
    )
    flecha(ax, 0.82, 0.64, 0.85, 0.67, TEAL, etiqueta="no")

    caja(
        ax,
        0.66,
        0.18,
        0.20,
        0.14,
        "replanificar_plan\n(motivo, condición)\nconserva pasos completados",
        NARANJA_CLARO,
        NARANJA,
        8.2,
    )
    flecha(ax, 0.76, 0.52, 0.76, 0.32, ROJO, etiqueta="sí")

    caja(
        ax,
        0.30,
        0.18,
        0.24,
        0.14,
        "Nueva ruta: alternativas de política,\nnota de crédito, escalamiento\n+ registrar_nota_caso",
        GRIS,
        AZUL,
        8.2,
    )
    flecha(ax, 0.66, 0.25, 0.54, 0.25, NARANJA)
    caja(ax, 0.01, 0.18, 0.22, 0.14, "Respuesta honesta\ny fundamentada\n(cita sección)", TEAL_CLARO, TEAL, 8.2)
    flecha(ax, 0.30, 0.25, 0.23, 0.25, TEAL)

    ax.text(
        0.5,
        0.075,
        "Condiciones que disparan la replanificación: PLAZO_VENCIDO · STOCK_INSUFICIENTE · "
        "CATEGORIA_EXCLUIDA · DESCUENTO_EXCLUSIVO · CONDICIONES_NO_CUMPLIDAS",
        ha="center",
        fontsize=8.2,
        color=AZUL,
    )
    fig.savefig(config.DOCS_DIR / "diagrama_decision.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def diagrama_memoria() -> None:
    fig, ax = _lienzo("Memoria, compresión y recuperación de contexto semántico", 12, 6.2)

    caja(ax, 0.02, 0.62, 0.18, 0.12, "Turno del\ncliente", GRIS, AZUL, 8.5, "bold")
    caja(ax, 0.25, 0.60, 0.26, 0.16, "Memoria de corto plazo\nventana deslizante (8 mensajes)\n+ resumen comprimido", TEAL_CLARO, TEAL, 8.5)
    flecha(ax, 0.20, 0.68, 0.25, 0.68)

    caja(ax, 0.25, 0.36, 0.26, 0.14, "¿Supera 12 mensajes?\n→ compresión por LLM", GRIS, AZUL, 8.5)
    flecha(ax, 0.38, 0.60, 0.38, 0.50, etiqueta="sí")

    caja(
        ax,
        0.60,
        0.36,
        0.38,
        0.19,
        "Memoria de largo plazo (data/memoria.json)\nhechos · preferencias · casos · resúmenes\n"
        "consolidación automática de folios",
        NARANJA_CLARO,
        NARANJA,
        8.5,
    )
    flecha(ax, 0.51, 0.43, 0.60, 0.43, etiqueta="resumen")

    caja(ax, 0.60, 0.62, 0.38, 0.14, "Recuperación semántica\nTF-IDF + coseno sobre recuerdos", GRIS, AZUL, 8.5)
    flecha(ax, 0.79, 0.55, 0.79, 0.62, NARANJA, "<|-|>")

    caja(
        ax,
        0.25,
        0.08,
        0.36,
        0.16,
        "Prompt del sistema\n[MEMORIA DE LARGO PLAZO]\n+ [RESUMEN] + chat_history",
        AZUL_CLARO,
        AZUL,
        8.5,
        "bold",
    )
    flecha(ax, 0.79, 0.62, 0.61, 0.19, AZUL, curvatura=-0.18, etiqueta="")
    flecha(ax, 0.32, 0.36, 0.32, 0.24, AZUL, etiqueta="ventana actual")

    ax.text(
        0.10,
        0.20,
        "La continuidad sobrevive\nal reinicio del proceso\ngracias a la persistencia JSON.",
        ha="left",
        fontsize=8.2,
        color=GRIS_TEXTO,
        style="italic",
        linespacing=1.4,
    )
    fig.savefig(config.DOCS_DIR / "diagrama_memoria.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    config.asegurar_directorios()
    diagrama_arquitectura()
    diagrama_decision()
    diagrama_memoria()
    for nombre in ("diagrama_arquitectura.png", "diagrama_decision.png", "diagrama_memoria.png"):
        print(f"[OK] {config.DOCS_DIR / nombre}")


if __name__ == "__main__":
    main()
