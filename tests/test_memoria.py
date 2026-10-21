"""Pruebas de los tres mecanismos de memoria (IL2.2 / IE3 / IE4)."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from src.memoria import GestorMemoria, MemoriaCortoPlazo, MemoriaLargoPlazo


def _largo(tmp_path) -> MemoriaLargoPlazo:
    return MemoriaLargoPlazo(ruta=tmp_path / "memoria.json")


def test_persistencia_entre_instancias(tmp_path):
    memoria = _largo(tmp_path)
    memoria.agregar("El cliente prefiere retiro en tienda", tipo="preferencia")
    memoria.agregar("Caso DEV-20261020-001-ABCD aprobado", tipo="caso")

    recargada = _largo(tmp_path)
    assert len(recargada.listar()) == 2
    assert recargada.listar("caso")[0].contenido.startswith("Caso DEV-")


def test_busqueda_semantica_ordena_por_relevancia(tmp_path):
    memoria = _largo(tmp_path)
    memoria.agregar("Horario de atención de lunes a viernes", tipo="hecho")
    memoria.agregar("Devolución de chaqueta aprobada con folio DEV-20261020-002-EEEE", tipo="caso")

    resultados = memoria.buscar_semantica("necesito devolver una chaqueta")
    assert resultados
    assert "Devolución" in resultados[0].contenido


def test_busqueda_semantica_ignora_tildes_y_mayusculas(tmp_path):
    memoria = _largo(tmp_path)
    memoria.agregar("Política de devoluciones: plazo de 30 días", tipo="hecho")

    assert memoria.buscar_semantica("DEVOLUCIONES") != []


def test_busqueda_memoria_vacia(tmp_path):
    memoria = _largo(tmp_path)
    assert memoria.buscar_semantica("devolución") == []
    assert memoria.resumen_memoria() == "(memoria de largo plazo vacía)"


def test_limpiar_memoria(tmp_path):
    memoria = _largo(tmp_path)
    memoria.agregar("dato")
    memoria.limpiar()
    assert memoria.listar() == []


def test_ventana_corto_plazo():
    corto = MemoriaCortoPlazo(ventana=4)
    for i in range(6):
        corto.registrar_turno(f"pregunta {i}", f"respuesta {i}")

    assert len(corto.mensajes) == 12
    ventana = corto.ventana_actual()
    assert len(ventana) == 4
    assert ventana[-1].content == "respuesta 5"


def test_compresion_de_historial(fake_llm):
    corto = MemoriaCortoPlazo(ventana=8)
    for i in range(7):
        corto.agregar(HumanMessage(content=f"pregunta {i}"))
        corto.agregar(AIMessage(content=f"respuesta {i}"))

    assert corto.excede() is True
    resumen = corto.comprimir(fake_llm)

    assert resumen == "respuesta simulada"
    assert corto.mensajes[0].content.startswith("[Resumen previo]")
    assert len(corto.mensajes) == 5


def test_gestor_persiste_resumen_en_largo_plazo(tmp_path, fake_llm, monkeypatch):
    from src import config

    monkeypatch.setattr(config, "TURNO_PARA_RESUMEN", 4)
    gestor = GestorMemoria(llm=fake_llm, largo_plazo=_largo(tmp_path))

    for i in range(2):
        gestor.registrar_turno(f"pregunta {i}", f"respuesta {i}")

    resumenes = gestor.largo.listar("resumen")
    assert len(resumenes) == 1
    assert "Resumen de conversación" in resumenes[0].contenido


def test_consolidar_traza_guarda_caso(tmp_path):
    gestor = GestorMemoria(largo_plazo=_largo(tmp_path))
    traza = [
        {
            "accion": "registrar_solicitud_devolucion",
            "entrada": {
                "cliente": "Camila Rojas",
                "sku": "URB-002",
                "motivo": "cambio de talla",
                "decision": "APROBADA_ONLINE",
                "dias_desde_recepcion": 12,
                "canal": "online",
            },
            "observacion": "SOLICITUD REGISTRADA - folio DEV-20261020-001-9F3A\n  Cliente: Camila Rojas",
        },
        {"accion": "consultar_stock", "entrada": {}, "observacion": "stock 8"},
    ]

    nuevos = gestor.consolidar_traza(traza)

    assert len(nuevos) == 1
    assert nuevos[0].tipo == "caso"
    assert "DEV-20261020-001-9F3A" in nuevos[0].contenido
    assert "Camila Rojas" in nuevos[0].contenido
    assert nuevos[0].metadata["folio"] == "DEV-20261020-001-9F3A"


def test_bloque_largo_plazo_recupera_recuerdo_relevante(tmp_path):
    gestor = GestorMemoria(largo_plazo=_largo(tmp_path))
    gestor.recordar("Caso DEV-1 - cliente Camila Rojas - SKU URB-002", tipo="caso")

    bloque = gestor.bloque_largo_plazo("hola soy Camila Rojas, ¿recuerdas mi caso?")
    assert "MEMORIA DE LARGO PLAZO" in bloque
    assert "Camila Rojas" in bloque


def test_bloque_largo_plazo_sin_recuerdos(tmp_path):
    gestor = GestorMemoria(largo_plazo=_largo(tmp_path))
    assert gestor.bloque_largo_plazo("hola") == "[MEMORIA] Sin interacciones previas registradas."


def test_bloque_completo_incluye_turnos(tmp_path):
    gestor = GestorMemoria(largo_plazo=_largo(tmp_path))
    gestor.registrar_turno("hola", "buenas tardes")

    bloque = gestor.bloque_completo("hola")
    assert "memoria de corto plazo" in bloque
    assert "buenas tardes" in bloque
