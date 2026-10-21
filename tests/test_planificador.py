"""Pruebas del planificador y de la replanificación adaptativa (IL2.3 / IE5)."""

from __future__ import annotations

import json

from src.planificador import Planificador


class FakePlanLLM:
    """Devuelve un plan JSON válido y permite cambiar la respuesta entre llamadas."""

    def __init__(self, planes: list[dict]):
        self.planes = planes
        self.llamadas = 0

    def invoke(self, _prompt):
        plan = self.planes[min(self.llamadas, len(self.planes) - 1)]
        self.llamadas += 1
        return type("Salida", (), {"content": json.dumps(plan, ensure_ascii=False)})()


def _plan(n: int = 3) -> dict:
    return {
        "pasos": [
            {
                "descripcion": f"Paso {i}",
                "prioridad": i,
                "herramienta_sugerida": "consultar_politica",
                "criterio_exito": f"Criterio {i}",
            }
            for i in range(n, 0, -1)
        ]
    }


def test_crear_plan_con_llm(tmp_path):
    planificador = Planificador(llm=FakePlanLLM([_plan(3)]), ruta=tmp_path / "plan.json")

    plan = planificador.crear("Resolver devolución", contexto="cliente online")

    assert plan.version == 1
    assert len(plan.pasos) == 3
    assert [p.prioridad for p in plan.pasos] == [1, 2, 3]
    assert planificador.progreso() == 0


def test_plan_se_persiste_en_disco(tmp_path):
    ruta = tmp_path / "plan.json"
    planificador = Planificador(llm=FakePlanLLM([_plan(4)]), ruta=ruta)
    planificador.crear("Objetivo persistente")

    recargado = Planificador(ruta=ruta)

    assert recargado.plan is not None
    assert recargado.plan.objetivo == "Objetivo persistente"
    assert len(recargado.plan.pasos) == 4


def test_marcar_pasos_y_progreso(tmp_path):
    planificador = Planificador(llm=FakePlanLLM([_plan(2)]), ruta=tmp_path / "plan.json")
    planificador.crear("Objetivo")

    planificador.marcar(1, "completado", "evidencia obtenida")
    planificador.marcar(2, "completado")

    assert planificador.progreso() == 100
    assert planificador.plan.estado_general == "completado"


def test_marcar_estado_invalido(tmp_path):
    planificador = Planificador(llm=FakePlanLLM([_plan(2)]), ruta=tmp_path / "plan.json")
    planificador.crear("Objetivo")

    assert "inválido" in planificador.marcar(1, "terminado")
    assert "fuera de rango" in planificador.marcar(9, "completado")


def test_replanificar_incrementa_version_y_conserva_completados(tmp_path):
    llm = FakePlanLLM([_plan(3), _plan(2)])
    planificador = Planificador(llm=llm, ruta=tmp_path / "plan.json")
    planificador.crear("Devolución dentro de plazo")
    planificador.marcar(1, "completado", "política consultada")

    salida = planificador.replanificar(
        motivo="El plazo de 30 días está vencido",
        condicion="PLAZO_VENCIDO",
    )

    assert "PLAN REPLANIFICADO (v2)" in salida
    assert planificador.plan.version == 2
    assert planificador.plan.estado_general == "replanificado"
    assert planificador.plan.pasos[0].estado == "completado"
    assert len(planificador.plan.historial_replan) == 1
    assert planificador.plan.historial_replan[0]["condicion"] == "PLAZO_VENCIDO"


def test_replanificar_sin_llm_usa_ruta_alternativa(tmp_path):
    planificador = Planificador(llm=None, ruta=tmp_path / "plan.json")
    planificador.crear("Objetivo", pasos=_plan(2)["pasos"])

    salida = planificador.replanificar(motivo="Sin stock", condicion="STOCK_INSUFICIENTE")

    assert "v2" in salida
    assert len(planificador.plan.pasos) == 2
    assert planificador.plan.pasos[0].herramienta_sugerida == "buscar_conocimiento"


def test_consultar_sin_plan(tmp_path):
    planificador = Planificador(ruta=tmp_path / "plan.json")
    assert "No hay un plan activo" in planificador.consultar()
    assert planificador.estado() == {"activo": False}


def test_estado_del_plan(tmp_path):
    planificador = Planificador(llm=FakePlanLLM([_plan(3)]), ruta=tmp_path / "plan.json")
    planificador.crear("Objetivo")
    estado = planificador.estado()
    assert estado["activo"] is True
    assert estado["version"] == 1
    assert estado["pasos"] == 3
