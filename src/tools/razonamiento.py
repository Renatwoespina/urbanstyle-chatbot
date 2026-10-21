"""Herramientas de **razonamiento** del agente UrbanStyle 2.0.

Dos familias:

- `evaluar_devolucion`: motor de reglas determinista que traduce la política
  organizacional en una decisión verificable. Es la fuente de las **señales
  adaptativas** que obligan al agente a replanificar.
- `calcular`: aritmética segura (subtotal, descuento, IVA, cuotas, diferencia
  de precio) usada para respaldar montos con evidencia numérica.
"""

from __future__ import annotations

import ast
import operator

from langchain_core.tools import StructuredTool

# Reglas extraídas de data/politica_devoluciones.txt
PLAZO_CAMBIO_DIAS = 30
GARANTIA_DEFECTO_DIAS = 90
NOTA_CREDITO_DIAS = 90
COSTO_ENVIO_DEVOLUCION = 3990
DESCUENTO_EXCLUIDO_PORCENTAJE = 50
CATEGORIAS_EXCLUIDAS = (
    "ropa interior",
    "traje de baño",
    "trajes de baño",
    "baño",
    "accesorios usados",
    "lentes",
    "joyería",
    "joyeria",
    "personalizado",
    "bordado",
)

_OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluar_nodo(nodo):
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        return nodo.value
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar_nodo(nodo.left), _evaluar_nodo(nodo.right))
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar_nodo(nodo.operand))
    raise ValueError("Expresión no permitida: usa sólo números y + - * / // % ** ( )")


def calcular(expresion: str) -> str:
    """Evalúa una expresión aritmética simple y devuelve el resultado formateado."""
    try:
        arbol = ast.parse(expresion.replace(",", ""), mode="eval")
        resultado = _evaluar_nodo(arbol.body)
    except ZeroDivisionError:
        return "Error: división por cero en la expresión."
    except Exception as exc:
        return f"Error al calcular '{expresion}': {exc}"
    if isinstance(resultado, float) and resultado.is_integer():
        resultado = int(resultado)
    return f"{expresion.strip()} = {resultado:,}".replace(",", ".")


def evaluar_devolucion(
    dias_desde_recepcion: int,
    cumple_condiciones: bool,
    categoria: str,
    canal: str,
    es_defectuoso: bool = False,
    descuento_porcentaje: float = 0.0,
    stock_reemplazo: int = -1,
) -> str:
    """Aplica la política de cambios y devoluciones y devuelve una decisión fundamentada.

    Devuelve la decisión, el fundamento (sección de la política), la acción
    sugerida y, si las condiciones cambiaron respecto del plan original, la
    señal `REPLANIFICACION_REQUERIDA` que obliga al agente a replanificar.
    """
    dias = int(dias_desde_recepcion)
    categoria_n = (categoria or "").strip().lower()
    canal_n = (canal or "tienda").strip().lower()
    resultado: dict = {"senal_adaptativa": None, "requiere_replan": False}

    # 1) Defectos de fabricación -> garantía de 90 días, no aplica el plazo de 30.
    if es_defectuoso:
        if dias <= GARANTIA_DEFECTO_DIAS:
            resultado.update(
                decision="GARANTIA_APLICABLE",
                aprobada=True,
                resolucion="Producto defectuoso cubierto por garantía de 90 días.",
                fundamento="Sección 7 (Productos defectuosos): no aplica el plazo de 30 días; UrbanStyle cubre todos los costos de envío y reposición.",
                siguiente_accion="Coordinar recogida del producto defectuoso y enviar reposición sin costo o devolver el dinero completo.",
                alternativas=["Reposición sin costo", "Devolución completa del dinero"],
            )
        else:
            resultado.update(
                decision="GARANTIA_VENCIDA",
                aprobada=False,
                resolucion=f"El defecto se reporta a los {dias} días; la garantía vence a los {GARANTIA_DEFECTO_DIAS} días.",
                fundamento="Sección 7 (Productos defectuosos): garantía de 90 días desde la recepción.",
                siguiente_accion="Escalar a soporte para evaluación excepcional.",
                requiere_replan=True,
                senal_adaptativa="GARANTIA_VENCIDA",
            )

    # 2) Categorías excluidas por higiene / personalización / descuento alto.
    elif any(palabra in categoria_n for palabra in CATEGORIAS_EXCLUIDAS):
        resultado.update(
            decision="NO_CAMBIABLE_CATEGORIA",
            aprobada=False,
            resolucion=f"La categoría '{categoria}' no está sujeta a cambios ni devoluciones.",
            fundamento="Sección 3 (Productos no cambiables): ropa interior y trajes de baño por razones de higiene; accesorios usados; descuentos superiores al 50%.",
            siguiente_accion="Ofrecer alternativas de buena fe y escalar a soporte si el cliente reclama.",
            requiere_replan=True,
            senal_adaptativa="CATEGORIA_EXCLUIDA",
        )

    # 3) Liquidaciones con descuento mayor al 50%.
    elif float(descuento_porcentaje or 0) > DESCUENTO_EXCLUIDO_PORCENTAJE:
        resultado.update(
            decision="NO_CAMBIABLE_DESCUENTO",
            aprobada=False,
            resolucion=f"Producto con {descuento_porcentaje}% de descuento (superior al 50%).",
            fundamento="Sección 3 (Productos no cambiables): productos en liquidación o con descuento superior al 50%.",
            siguiente_accion="Informar la condición y ofrecer contacto con soporte.",
            requiere_replan=True,
            senal_adaptativa="DESCUENTO_EXCLUSIVO",
        )

    # 4) Plazo vencido.
    elif dias > PLAZO_CAMBIO_DIAS:
        resultado.update(
            decision="RECHAZADA_POR_PLAZO",
            aprobada=False,
            resolucion=f"Solicitud a los {dias} días; el plazo máximo es de {PLAZO_CAMBIO_DIAS} días corridos.",
            fundamento="Sección 1 (Plazo para cambios o devoluciones): 30 días corridos desde la fecha de recepción.",
            siguiente_accion="Buscar alternativas permitidas (contacto con soporte, beneficios Club UrbanStyle) y registrar la negativa.",
            requiere_replan=True,
            senal_adaptativa="PLAZO_VENCIDO",
        )

    # 5) Condiciones del producto no cumplidas.
    elif not cumple_condiciones:
        resultado.update(
            decision="RECHAZADA_CONDICIONES",
            aprobada=False,
            resolucion="El producto no cumple las condiciones exigidas (sin usar, con etiquetas, empaque original, con boleta).",
            fundamento="Sección 2 (Condiciones del producto): cuatro requisitos acumulativos.",
            siguiente_accion="Explicar el requisito incumplido y ofrecer atención presencial para validación.",
            requiere_replan=True,
            senal_adaptativa="CONDICIONES_NO_CUMPLIDAS",
        )

    # 6) Aprobada.
    else:
        if canal_n == "online":
            resultado.update(
                decision="APROBADA_ONLINE",
                aprobada=True,
                resolucion="Cambio o devolución de pedido online aprobada.",
                fundamento="Sección 6 (Pedidos online): recogida en la dirección indicada, costo de envío de devolución de $3.990 asumido por el cliente, proceso en 5 días hábiles.",
                siguiente_accion=f"Coordinar recogida, cobrar ${COSTO_ENVIO_DEVOLUCION} de envío y procesar cambio o nota de crédito en 5 días hábiles.",
                alternativas=["Cambio por producto de igual valor", f"Nota de crédito válida {NOTA_CREDITO_DIAS} días"],
            )
        else:
            resultado.update(
                decision="APROBADA_TIENDA",
                aprobada=True,
                resolucion="Cambio o devolución en tienda aprobada.",
                fundamento="Sección 4 y 5 (Proceso en tienda): cambio inmediato con diferencia de pago si corresponde; si es de menor valor se emite nota de crédito; no se devuelven efectivos.",
                siguiente_accion="Validar producto en caja, realizar el cambio o emitir nota de crédito.",
                alternativas=["Cambio inmediato por igual o mayor valor", f"Nota de crédito válida {NOTA_CREDITO_DIAS} días", "No aplica devolución en efectivo"],
            )
        # 6b) La aprobación puede tropezar con stock insuficiente.
        if int(stock_reemplazo) == 0:
            resultado.update(
                decision="APROBADA_SIN_STOCK",
                aprobada=True,
                requiere_replan=True,
                senal_adaptativa="STOCK_INSUFICIENTE",
                resolucion="Solicitud válida, pero no hay stock para el reemplazo.",
                siguiente_accion="Ofrecer nota de crédito o notificación de llegada de stock; no se puede ejecutar el plan de cambio inmediato.",
            )

    decision = resultado["decision"]
    aprobada = resultado["aprobada"]
    lineas = [
        f"DECISIÓN: {decision} | {'APROBADA' if aprobada else 'NO APROBADA'}",
        f"Resolución: {resultado['resolucion']}",
        f"Fundamento: {resultado['fundamento']}",
        f"Acción sugerida: {resultado['siguiente_accion']}",
    ]
    if resultado.get("alternativas"):
        lineas.append("Alternativas permitidas: " + " | ".join(resultado["alternativas"]))
    lineas.append(
        f"Parámetros evaluados: días={dias}, cumple_condiciones={cumple_condiciones}, "
        f"categoría={categoria or 'n/d'}, canal={canal_n}, defectuoso={es_defectuoso}, "
        f"descuento={descuento_porcentaje}%, stock_reemplazo={stock_reemplazo}"
    )
    if resultado.get("requiere_replan"):
        lineas.append("")
        lineas.append(
            "[SEÑAL ADAPTATIVA] REPLANIFICACION_REQUERIDA: "
            f"condición cambiante '{resultado['senal_adaptativa']}' hace inviable el plan original. "
            "Antes de responder al cliente debes llamar a `replanificar_plan` con esta condición "
            "y ejecutar la nueva ruta."
        )
    else:
        lineas.append("[SEÑAL ADAPTATIVA] SIN_CAMBIO: el plan original sigue siendo válido.")
    return "\n".join(lineas)


def construir_herramientas_razonamiento() -> list:
    return [
        StructuredTool.from_function(
            func=evaluar_devolucion,
            name="evaluar_devolucion",
            description=(
                "Motor de reglas de la política de UrbanStyle. Evalúa una solicitud de cambio/devolución "
                "(días desde recepción, condiciones del producto, categoría, canal, si es defectuoso, "
                "descuento y stock de reemplazo) y devuelve la decisión fundamentada. "
                "Si devuelve REPLANIFICACION_REQUERIDA debes replanificar antes de responder."
            ),
            tags=["razonamiento", "decision"],
        ),
        StructuredTool.from_function(
            func=calcular,
            name="calcular",
            description=(
                "Evaluador aritmético seguro para montos: suma, resta, multiplicación, división, "
                "módulo, potencia y paréntesis. Úsalo para diferencia de precio, descuentos, "
                "costos de envío y cuotas."
            ),
            tags=["razonamiento"],
        ),
    ]
