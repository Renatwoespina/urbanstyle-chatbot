"""Pruebas de orquestación del agente sin consumir cuota del LLM."""

from __future__ import annotations

from src.agente import AgenteUrbanStyle
from src.memoria import MemoriaLargoPlazo


class FakeAccion:
    def __init__(self, tool: str, tool_input: dict):
        self.tool = tool
        self.tool_input = tool_input


class FakeExecutor:
    """Sustituye a AgentExecutor: devuelve una traza fija y guarda la entrada."""

    def __init__(self, salida: dict):
        self.salida = salida
        self.entradas: list[dict] = []

    def invoke(self, entradas: dict) -> dict:
        self.entradas.append(entradas)
        return self.salida


TRAZA_CASO = [
    (
        FakeAccion("planificar", {"objetivo": "Resolver devolución"}),
        "PLAN v1 CREADO con 5 pasos.",
    ),
    (
        FakeAccion(
            "registrar_solicitud_devolucion",
            {
                "sku": "URB-002",
                "cliente": "Camila Rojas",
                "dias_desde_recepcion": 12,
                "motivo": "cambio de talla",
                "canal": "online",
                "decision": "APROBADA_ONLINE",
            },
        ),
        "SOLICITUD REGISTRADA - folio DEV-20261020-001-9F3A\n  Cliente: Camila Rojas",
    ),
]


def _agente(tmp_path, fake_llm, salida=None) -> AgenteUrbanStyle:
    agente = AgenteUrbanStyle(
        llm=fake_llm,
        ruta_memoria=tmp_path / "memoria.json",
        ruta_plan=tmp_path / "plan.json",
    )
    agente.executor = FakeExecutor(salida or {"output": "Respuesta simulada.", "intermediate_steps": TRAZA_CASO})
    return agente


def test_preguntar_devuelve_traza_y_respuesta(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)

    resultado = agente.preguntar("Compré online hace 12 días, quiero cambiarlo")

    assert resultado["respuesta"] == "Respuesta simulada."
    assert resultado["herramientas_usadas"] == ["planificar", "registrar_solicitud_devolucion"]
    assert resultado["plan"] == {"activo": False}
    assert resultado["memoria"]["turnos_corto_plazo"] == 2


def test_preguntar_inyecta_memoria_y_ventana(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    agente.memoria.recordar("Caso previo del cliente Camila Rojas", tipo="caso")

    agente.preguntar("Hola, soy Camila Rojas")

    entradas = agente.executor.entradas[0]
    assert "Camila Rojas" in entradas["memoria"]
    assert entradas["input"] == "Hola, soy Camila Rojas"
    assert isinstance(entradas["chat_history"], list)


def test_preguntar_consolida_caso_en_memoria_largo_plazo(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)

    resultado = agente.preguntar("Quiero cambiar el SKU URB-002")

    assert len(resultado["recuerdos_nuevos"]) == 1
    assert "DEV-20261020-001-9F3A" in resultado["recuerdos_nuevos"][0]

    recargada = MemoriaLargoPlazo(ruta=tmp_path / "memoria.json")
    assert len(recargada.listar("caso")) == 1


def test_preguntar_vacio_no_invoca_al_agente(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    assert agente.preguntar("   ")["respuesta"] == ""
    assert agente.executor.entradas == []


def test_formatear_traza_trunca_observaciones(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    traza = agente._formatear_traza([(FakeAccion("calcular", {"expresion": "1+1"}), "x" * 2000)])
    assert traza[0]["accion"] == "calcular"
    assert traza[0]["entrada"] == {"expresion": "1+1"}
    assert len(traza[0]["observacion"]) == 900


def test_supervisar_usa_reflexion(tmp_path, fake_llm, monkeypatch):
    agente = _agente(tmp_path, fake_llm)
    monkeypatch.setattr("src.agente.invocar_llm", lambda sistema, usuario: "Revisión OK")

    salida = agente.supervisar({"entrada": "hola", "traza": [], "respuesta": "buenas"})

    assert salida == "Revisión OK"


def test_reiniciar_sesion_conserva_largo_plazo(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    agente.preguntar("Quiero cambiar el SKU URB-002")

    mensaje = agente.reiniciar_sesion()

    assert "reiniciada" in mensaje
    assert agente.memoria.estado()["turnos_corto_plazo"] == 0
    assert agente.memoria.estado()["recuerdos_largo_plazo"] == 1


def test_estado_del_agente(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    estado = agente.estado()
    assert estado["total_herramientas"] == 13
    assert set(estado["herramientas"]) == {"consulta", "escritura", "razonamiento"}


def test_transcript_incluye_evidencia(tmp_path, fake_llm):
    agente = _agente(tmp_path, fake_llm)
    resultado = agente.preguntar("Quiero cambiar el SKU URB-002")
    texto = agente.transcript(resultado)
    assert "ENTRADA:" in texto
    assert "TOOL registrar_solicitud_devolucion" in texto
    assert "RESPUESTA:" in texto
