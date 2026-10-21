"""Planificación de tareas y toma de decisiones adaptativas (IL2.3 / IE5).

El `Planificador` mantiene un plan explícito de pasos priorizados que el agente
puede consultar, actualizar y —lo más importante— **replanificar** cuando una
herramienta devuelve una señal de cambio de condiciones (plazo vencido, stock
insuficiente, producto no cambiable, etc.).

El plan se persiste en `data/plan_actual.json`, de modo que la continuidad de la
tarea también sobrevive a un reinicio del proceso.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from src import config

ESTADOS_PASO = ("pendiente", "en_curso", "completado", "bloqueado")

SISTEMA_PLAN = """Eres el planificador de tareas del área de atención al cliente de UrbanStyle Chile.
Recibirás un objetivo y el contexto disponible, y debes devolver UN plan de ejecución.

REGLAS:
- Entre {min} y {max} pasos, ordenados por prioridad de ejecución (el primero es el más urgente).
- Cada paso debe ser una acción concreta y verificable, no una idea general.
- Asigna a cada paso la herramienta sugerida entre: buscar_conocimiento, consultar_producto,
  consultar_stock, consultar_politica, evaluar_devolucion, calcular, registrar_solicitud_devolucion,
  guardar_en_memoria, registrar_nota_caso.
- Devuelve SOLO JSON válido con esta forma:
{{"pasos": [{{"descripcion": "...", "prioridad": 1, "herramienta_sugerida": "...", "criterio_exito": "..."}}]}}"""


@dataclass
class Paso:
    descripcion: str
    prioridad: int
    herramienta_sugerida: str
    criterio_exito: str
    estado: str = "pendiente"
    nota: str = ""

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Plan:
    objetivo: str
    pasos: list[Paso] = field(default_factory=list)
    version: int = 1
    creado: str = ""
    historial_replan: list[dict] = field(default_factory=list)
    estado_general: str = "en_ejecucion"

    def a_dict(self) -> dict:
        return {
            "objetivo": self.objetivo,
            "pasos": [p.a_dict() for p in self.pasos],
            "version": self.version,
            "creado": self.creado,
            "historial_replan": self.historial_replan,
            "estado_general": self.estado_general,
        }


class Planificador:
    """Administra el plan vigente, su progreso y sus replanificaciones."""

    def __init__(self, llm=None, ruta=config.PLAN_FILE):
        self.llm = llm
        self.ruta = ruta
        self.plan: Plan | None = None
        self.cargar()

    # --- persistencia ---
    def cargar(self) -> None:
        if not self.ruta.exists():
            return
        with open(self.ruta, encoding="utf-8") as fh:
            data = json.load(fh)
        pasos = [Paso(**p) for p in data.get("pasos", [])]
        self.plan = Plan(
            objetivo=data.get("objetivo", ""),
            pasos=pasos,
            version=data.get("version", 1),
            creado=data.get("creado", ""),
            historial_replan=data.get("historial_replan", []),
            estado_general=data.get("estado_general", "en_ejecucion"),
        )

    def guardar(self) -> None:
        if self.plan is None:
            return
        with open(self.ruta, "w", encoding="utf-8") as fh:
            json.dump(self.plan.a_dict(), fh, ensure_ascii=False, indent=2)

    # --- generación del plan ---
    def _generar_con_llm(self, objetivo: str, contexto: str) -> list[dict]:
        prompt = (
            SISTEMA_PLAN.format(min=config.MIN_PASOS_PLAN, max=config.MAX_PASOS_PLAN)
            + f"\n\nOBJETIVO: {objetivo}\nCONTEXTO: {contexto or '(ninguno)'}"
        )
        salida = self.llm.invoke(prompt)
        texto = getattr(salida, "content", str(salida)).strip()
        if texto.startswith("```"):
            texto = texto.strip("`").removeprefix("json").strip()
        inicio, fin = texto.find("{"), texto.rfind("}")
        data = json.loads(texto[inicio : fin + 1])
        pasos = data.get("pasos", [])[: config.MAX_PASOS_PLAN]
        return pasos

    def crear(self, objetivo: str, contexto: str = "", pasos: list[dict] | None = None) -> Plan:
        if pasos is None:
            if self.llm is None:
                raise RuntimeError("Se requiere un LLM para generar el plan automáticamente")
            pasos = self._generar_con_llm(objetivo, contexto)

        construidos = [
            Paso(
                descripcion=str(p.get("descripcion", "")).strip(),
                prioridad=int(p.get("prioridad", i + 1)),
                herramienta_sugerida=str(p.get("herramienta_sugerida", "")),
                criterio_exito=str(p.get("criterio_exito", "")),
                estado="pendiente",
            )
            for i, p in enumerate(pasos)
        ]
        construidos.sort(key=lambda p: p.prioridad)
        self.plan = Plan(
            objetivo=objetivo,
            pasos=construidos,
            version=1,
            creado=datetime.now().isoformat(timespec="seconds"),
        )
        self.guardar()
        return self.plan

    # --- consulta y actualización ---
    def consultar(self) -> str:
        if self.plan is None:
            return "No hay un plan activo. Usa `planificar` para crear uno."
        lineas = [
            f"PLAN v{self.plan.version} - {self.plan.estado_general.upper()}",
            f"Objetivo: {self.plan.objetivo}",
            f"Progreso: {self.progreso()}%",
        ]
        for i, p in enumerate(self.plan.pasos, start=1):
            mark = {"pendiente": "[ ]", "en_curso": "[>]", "completado": "[x]", "bloqueado": "[!]"}[p.estado]
            extra = f" | nota: {p.nota}" if p.nota else ""
            lineas.append(f"  {i}. {mark} {p.descripcion} (herramienta: {p.herramienta_sugerida}){extra}")
        if self.plan.historial_replan:
            ultimo = self.plan.historial_replan[-1]
            lineas.append(
                f"  Última replanificación (v{ultimo.get('version')}): {ultimo.get('motivo')}"
            )
        return "\n".join(lineas)

    def progreso(self) -> int:
        if not self.plan or not self.plan.pasos:
            return 0
        hechos = sum(1 for p in self.plan.pasos if p.estado == "completado")
        return int(100 * hechos / len(self.plan.pasos))

    def resumen_pasos(self) -> str:
        """Lista compacta de pasos (para no gastar tokens en la observación)."""
        if not self.plan:
            return "Sin plan activo."
        return "\n".join(
            f"{i}. [{p.estado}] {p.descripcion} -> {p.herramienta_sugerida}"
            for i, p in enumerate(self.plan.pasos, start=1)
        )

    def marcar(self, indice: int, estado: str, nota: str = "") -> str:
        if self.plan is None:
            return "No hay plan activo."
        if estado not in ESTADOS_PASO:
            return f"Estado inválido '{estado}'. Válidos: {', '.join(ESTADOS_PASO)}"
        if not 1 <= indice <= len(self.plan.pasos):
            return f"Paso {indice} fuera de rango (1..{len(self.plan.pasos)})."
        paso = self.plan.pasos[indice - 1]
        paso.estado = estado
        paso.nota = nota or paso.nota
        if all(p.estado == "completado" for p in self.plan.pasos):
            self.plan.estado_general = "completado"
        elif estado == "bloqueado":
            self.plan.estado_general = "bloqueado"
        self.guardar()
        siguiente = next(
            (f"{i}. {p.descripcion}" for i, p in enumerate(self.plan.pasos, 1) if p.estado != "completado"),
            "ninguno (plan completo)",
        )
        return (
            f"Paso {indice} -> {estado}. Progreso {self.progreso()}% "
            f"(plan {self.plan.estado_general}). Siguiente pendiente: {siguiente}"
        )

    # --- decisión adaptativa ---
    def replanificar(self, motivo: str, condicion: str = "", contexto: str = "") -> str:
        """Genera una nueva versión del plan ante un cambio de condiciones.

        Conserva los pasos ya completados y sustituye los pendientes por una
        ruta alternativa calculada por el LLM con el nuevo contexto.
        """
        if self.plan is None:
            return "No hay plan activo que replanificar."

        completados = [
            p for p in self.plan.pasos if p.estado == "completado"
        ]
        objetivo_nuevo = f"{self.plan.objetivo} [replanificado: {condicion or motivo}]"

        nuevos: list[dict] = []
        if self.llm is not None:
            contexto_plan = (
                f"Objetivo original: {self.plan.objetivo}\n"
                f"Condición cambiante detectada: {condicion or motivo}\n"
                f"Motivo: {motivo}\n"
                f"Ya completado: {'; '.join(p.descripcion for p in completados) or 'nada'}\n"
                f"Contexto adicional: {contexto}"
            )
            try:
                nuevos = self._generar_con_llm(objetivo_nuevo, contexto_plan)
            except Exception:
                nuevos = []
        if not nuevos:
            nuevos = [
                {
                    "descripcion": f"Reevaluar alternativas ante: {condicion or motivo}",
                    "prioridad": 1,
                    "herramienta_sugerida": "buscar_conocimiento",
                    "criterio_exito": "Identificar alternativas permitidas por política",
                },
                {
                    "descripcion": "Proponer alternativa viable al cliente y registrar decisión",
                    "prioridad": 2,
                    "herramienta_sugerida": "registrar_nota_caso",
                    "criterio_exito": "Cliente informado y caso anotado",
                },
            ]

        pendientes = [
            Paso(
                descripcion=str(p.get("descripcion", "")).strip(),
                prioridad=int(p.get("prioridad", i + 1)),
                herramienta_sugerida=str(p.get("herramienta_sugerida", "")),
                criterio_exito=str(p.get("criterio_exito", "")),
            )
            for i, p in enumerate(nuevos[: config.MAX_PASOS_PLAN])
        ]
        pendientes.sort(key=lambda p: p.prioridad)

        self.plan.pasos = completados + pendientes
        for i, p in enumerate(self.plan.pasos, start=1):
            p.prioridad = i
        self.plan.version += 1
        self.plan.estado_general = "replanificado"
        self.plan.historial_replan.append(
            {
                "version": self.plan.version,
                "motivo": motivo,
                "condicion": condicion,
                "fecha": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.guardar()
        return (
            f"PLAN REPLANIFICADO (v{self.plan.version}). Motivo: {motivo}\n"
            f"Condición cambiante: {condicion or 'n/a'}\n"
            f"Se conservan {len(completados)} pasos completados.\n"
            f"{self.resumen_pasos()}\n"
            "Ejecuta la nueva ruta y actualiza los pasos con `actualizar_plan`."
        )

    def estado(self) -> dict[str, Any]:
        if self.plan is None:
            return {"activo": False}
        return {
            "activo": True,
            "version": self.plan.version,
            "progreso": self.progreso(),
            "estado_general": self.plan.estado_general,
            "pasos": len(self.plan.pasos),
            "replanificaciones": len(self.plan.historial_replan),
        }
