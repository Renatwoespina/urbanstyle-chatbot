"""Herramientas de **consulta** (lectura) del agente UrbanStyle 2.0.

Todas son de solo lectura: leen el corpus documental (RAG TF-IDF), el catálogo
en CSV o la política de devoluciones, y devuelven evidencia textual que el agente
usa para razonar. Ninguna modifica estado.
"""

from __future__ import annotations

import csv

from langchain_core.tools import StructuredTool

from src import config


def _cargar_catalogo() -> list[dict]:
    with open(config.CATALOGO_CSV, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ficha(row: dict) -> str:
    return (
        f"SKU: {row['sku']} | Producto: {row['nombre'].strip()} | Categoría: {row['categoria'].strip()}\n"
        f"Precio: ${row['precio_stock']} CLP | Stock: {row['stock']} unidades\n"
        f"Tallas: {row['talla']} | Colores: {row['color']}\n"
        f"Descripción: {row['descripcion'].strip()}"
    )


def buscar_conocimiento(consulta: str, retriever) -> str:
    """Busca en el corpus documental (FAQ, políticas, guía de tallas) lo relevante a la consulta."""
    contexto, fuentes = recuperar_contexto(retriever, consulta)
    if not contexto:
        return "No hay evidencia documental para esa consulta. Indica al cliente que contacte soporte."
    return f"[EVIDENCIA DOCUMENTAL - fuentes: {', '.join(fuentes)}]\n{contexto}"


def recuperar_contexto(retriever, consulta: str, fuentes=None, k=None):
    from src.rag_pipeline import recuperar_fragments

    return recuperar_fragments(retriever, consulta, fuentes=fuentes, k=k)


def consultar_producto(termino: str) -> str:
    """Consulta el catálogo por nombre, SKU o categoría. Devuelve fichas con precio, stock, tallas y colores."""
    termino = termino.strip().lower()
    if not termino:
        return "Debes indicar un nombre, SKU o categoría."
    filas = _cargar_catalogo()
    if termino in ("catálogo", "catalogo", "todos", "listado"):
        coincidencias = filas
    else:
        coincidencias = [
            r
            for r in filas
            if termino in r["nombre"].lower()
            or termino in r["sku"].lower()
            or termino in r["categoria"].lower()
        ]
    if not coincidencias:
        sugerencias = [r["nombre"].strip() for r in filas[:5]]
        return (
            f"No encontré productos para '{termino}'. "
            f"Productos disponibles (muestra): {', '.join(sugerencias)}. "
            "Prueba con otro término o consulta el catálogo completo con `consultar_producto('catálogo')`."
        )
    return "\n\n".join(_ficha(r) for r in coincidencias[:8])


def consultar_stock(termino: str, talla: str = "") -> str:
    """Consulta disponibilidad de stock de un producto, opcionalmente filtrando por talla."""
    ficha = consultar_producto(termino)
    if ficha.startswith("No encontré") or ficha.startswith("Debes"):
        return ficha
    filas = _cargar_catalogo()
    termino = termino.strip().lower()
    fila = next(
        (r for r in filas if termino in r["sku"].lower() or termino in r["nombre"].lower()),
        None,
    )
    if fila is None:
        return ficha
    stock = int(fila["stock"])
    talla = talla.strip().upper()
    if stock <= 0:
        estado = "SIN STOCK"
    elif stock <= 10:
        estado = "STOCK BAJO"
    else:
        estado = "DISPONIBLE"
    linea_talla = f" Talla '{talla}' {'sí' if talla and talla in fila['talla'].upper().split('/') else 'no'} figura en el catálogo." if talla else ""
    return (
        f"SKU {fila['sku']} ({fila['nombre'].strip()}): stock total {stock} unidades -> {estado}.{linea_talla}\n"
        f"Tallas listadas: {fila['talla']}."
    )


def consultar_politica(tema: str, retriever) -> str:
    """Recupera únicamente los pasajes de la política de cambios y devoluciones relacionados con el tema."""
    contexto, fuentes = recuperar_contexto(
        retriever, tema, fuentes=["politica_devoluciones"], k=3
    )
    if not contexto:
        contexto, fuentes = recuperar_contexto(retriever, tema, fuentes=None, k=2)
        return (
            "[POLÍTICA] No hay un pasaje exacto en la política de devoluciones. "
            f"Evidencia general:\n{contexto}\nFuentes: {', '.join(fuentes)}"
        )
    return f"[POLÍTICA DE CAMBIOS Y DEVOLUCIONES - {', '.join(fuentes)}]\n{contexto}"


def construir_herramientas_consulta(retriever) -> list:
    def buscar_conocimiento_tool(consulta: str) -> str:
        """Consulta semántica (RAG TF-IDF) sobre el corpus documental de UrbanStyle."""
        return buscar_conocimiento(consulta, retriever=retriever)

    def consultar_politica_tool(tema: str) -> str:
        """Recupera sólo los pasajes de la política de cambios y devoluciones aplicables."""
        return consultar_politica(tema, retriever=retriever)

    return [
        StructuredTool.from_function(
            func=buscar_conocimiento_tool,
            name="buscar_conocimiento",
            description=(
                "Consulta semántica (RAG TF-IDF) sobre el corpus documental de UrbanStyle: "
                "FAQ, política de devoluciones y guía de tallas. Úsala para cualquier duda "
                "de proceso, horarios, envíos, métodos de pago o reglas de cambio."
            ),
            tags=["consulta"],
        ),
        StructuredTool.from_function(
            func=consultar_producto,
            name="consultar_producto",
            description=(
                "Busca en el catálogo de productos por nombre, SKU o categoría y devuelve "
                "precio, stock, tallas y colores. Úsala antes de prometer precio o disponibilidad."
            ),
            tags=["consulta"],
        ),
        StructuredTool.from_function(
            func=consultar_stock,
            name="consultar_stock",
            description=(
                "Consulta el stock total de un producto y su estado (DISPONIBLE / STOCK BAJO / "
                "SIN STOCK), con opción de filtrar por talla. Imprescindible para evaluar cambios."
            ),
            tags=["consulta"],
        ),
        StructuredTool.from_function(
            func=consultar_politica_tool,
            name="consultar_politica",
            description=(
                "Recupera sólo los pasajes de la política de cambios y devoluciones aplicables "
                "a un tema (plazo, condiciones, productos no cambiables, nota de crédito, defectos)."
            ),
            tags=["consulta"],
        ),
    ]
