"""Catálogo de herramientas del agente UrbanStyle 2.0.

Agrupa las tres familias exigidas por IL2.1 / IE1:

- **consulta**: lectura de corpus documental, catálogo y política.
- **escritura**: persistencia de solicitudes, notas de caso y memoria.
- **razonamiento**: motor de decisiones, aritmética y planificación.

Además aplica una **caché de evidencias** a las herramientas deterministas: si el
agente repite la misma consulta (habitual al replanificar), no se vuelve a
ejecutar ni se consume cuota del LLM.
"""

from __future__ import annotations

import functools

from langchain_core.tools import StructuredTool

from src.tools.consulta import construir_herramientas_consulta
from src.tools.escritura import construir_herramientas_escritura
from src.tools.planificacion import construir_herramientas_planificacion
from src.tools.razonamiento import construir_herramientas_razonamiento

CATEGORIAS = ("consulta", "escritura", "razonamiento")

HERRAMIENTAS_CACHEABLES = {
    "buscar_conocimiento",
    "consultar_producto",
    "consultar_stock",
    "consultar_politica",
    "calcular",
    "evaluar_devolucion",
}


def _con_cache(herramienta, cache: dict):
    """Envuelve el callable de una herramienta determinista con memoización por turno."""
    if herramienta.name not in HERRAMIENTAS_CACHEABLES:
        return herramienta
    original = herramienta.func

    @functools.wraps(original)
    def envuelto(*args, **kwargs):
        clave = (herramienta.name,) + tuple(args) + tuple(sorted(kwargs.items()))
        if clave in cache:
            return "[caché de evidencia] " + cache[clave]
        valor = original(*args, **kwargs)
        cache[clave] = valor
        return valor

    return StructuredTool.from_function(
        func=envuelto,
        name=herramienta.name,
        description=herramienta.description,
        tags=herramienta.tags,
    )


def construir_herramientas(retriever, gestor_memoria, planificador, cache: dict | None = None) -> list:
    cache = {} if cache is None else cache
    herramientas: list = []
    herramientas += construir_herramientas_consulta(retriever)
    herramientas += construir_herramientas_escritura(gestor_memoria)
    herramientas += construir_herramientas_razonamiento()
    herramientas += construir_herramientas_planificacion(planificador)
    return [_con_cache(h, cache) for h in herramientas]


def clasificar_herramientas(herramientas: list) -> dict[str, list[str]]:
    agrupadas: dict[str, list[str]] = {c: [] for c in CATEGORIAS}
    for h in herramientas:
        categorias = set(getattr(h, "tags", []) or []) & set(CATEGORIAS)
        for c in categorias or {"razonamiento"}:
            agrupadas[c].append(h.name)
    return agrupadas


__all__ = ["construir_herramientas", "clasificar_herramientas", "CATEGORIAS"]
