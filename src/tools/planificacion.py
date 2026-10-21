"""Herramientas de **planificación** del agente UrbanStyle 2.0.

Expone el `Planificador` como herramientas invocables por el agente, de modo que
la planificación deje de ser implícita en el prompt y pase a ser un artefacto
persistente, consultable, priorizado y replanificable (IE5 / IL2.3).
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool


def construir_herramientas_planificacion(planificador) -> list:
    def planificar(objetivo: str, contexto: str = "") -> str:
        """Crea un plan de tareas priorizado para un objetivo y lo deja activo.

        Debe ser la PRIMERA acción cuando la tarea tenga varias etapas o
        condiciones inciertas. Genera entre 3 y 6 pasos verificables con la
        herramienta sugerida para cada uno.
        """
        plan = planificador.crear(objetivo=objetivo, contexto=contexto)
        return (
            f"PLAN v{plan.version} CREADO con {len(plan.pasos)} pasos.\n"
            f"{planificador.resumen_pasos()}\n"
            "Ejecútalos en orden con tus herramientas y marca el avance con `actualizar_plan`."
        )

    def consultar_plan() -> str:
        """Devuelve el plan activo, su progreso, el estado de cada paso y la última replanificación."""
        return planificador.consultar()

    def actualizar_plan(paso: int, estado: str, nota: str = "") -> str:
        """Marca un paso del plan activo como completado, en curso o bloqueado, con una nota opcional."""
        return planificador.marcar(int(paso), estado, nota)

    def replanificar_plan(motivo: str, condicion: str = "", contexto: str = "") -> str:
        """Genera una nueva versión del plan ante un cambio de condiciones.

        Úsala OBLIGATORIAMENTE cuando `evaluar_devolucion` devuelva
        REPLANIFICACION_REQUERIDA, o cuando aparezca un impedimento no previsto
        (stock insuficiente, plazo vencido, producto excluido). Conserva los pasos
        ya completados y calcula una ruta alternativa.
        """
        return planificador.replanificar(
            motivo=motivo, condicion=condicion, contexto=contexto
        )

    return [
        StructuredTool.from_function(
            func=planificar,
            name="planificar",
            description=(
                "Crea un plan de tareas priorizado (3 a 6 pasos, cada uno con herramienta "
                "sugerida y criterio de éxito) y lo deja activo para seguimiento."
            ),
            tags=["razonamiento", "planificacion"],
        ),
        StructuredTool.from_function(
            func=consultar_plan,
            name="consultar_plan",
            description="Muestra el plan activo, su progreso porcentual y el estado de cada paso.",
            tags=["razonamiento", "planificacion"],
        ),
        StructuredTool.from_function(
            func=actualizar_plan,
            name="actualizar_plan",
            description=(
                "Actualiza el estado de un paso del plan activo "
                "(pendiente | en_curso | completado | bloqueado) con una nota opcional."
            ),
            tags=["razonamiento", "planificacion"],
        ),
        StructuredTool.from_function(
            func=replanificar_plan,
            name="replanificar_plan",
            description=(
                "Reemplaza los pasos pendientes del plan por una nueva ruta ante un cambio de "
                "condiciones, conservando lo ya completado e incrementando la versión del plan."
            ),
            tags=["razonamiento", "planificacion", "adaptativo"],
        ),
    ]
