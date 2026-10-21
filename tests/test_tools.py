"""Pruebas de las 13 herramientas: consulta, escritura y razonamiento (IL2.1 / IE1)."""

from __future__ import annotations

import json
import re

import pytest

from src import config
from src.memoria import GestorMemoria, MemoriaLargoPlazo
from src.planificador import Planificador
from src.tools import CATEGORIAS, clasificar_herramientas, construir_herramientas
from src.tools.consulta import consultar_politica, consultar_producto, consultar_stock
from src.tools.escritura import registrar_nota_caso, registrar_solicitud_devolucion
from src.tools.razonamiento import calcular, evaluar_devolucion


# --------------------------- razonamiento ---------------------------
def test_evaluar_devolucion_online_dentro_de_plazo():
    salida = evaluar_devolucion(
        dias_desde_recepcion=12, cumple_condiciones=True, categoria="ropa", canal="online"
    )
    assert "DECISIÓN: APROBADA_ONLINE" in salida
    assert "SIN_CAMBIO" in salida
    assert "3.990" in salida


def test_evaluar_devolucion_tienda():
    salida = evaluar_devolucion(
        dias_desde_recepcion=5, cumple_condiciones=True, categoria="ropa", canal="tienda"
    )
    assert "APROBADA_TIENDA" in salida


def test_evaluar_devolucion_plazo_vencido_genera_replanificacion():
    salida = evaluar_devolucion(
        dias_desde_recepcion=45, cumple_condiciones=True, categoria="ropa", canal="tienda"
    )
    assert "RECHAZADA_POR_PLAZO" in salida
    assert "REPLANIFICACION_REQUERIDA" in salida
    assert "PLAZO_VENCIDO" in salida


def test_evaluar_devolucion_defectuoso_aplica_garantia():
    salida = evaluar_devolucion(
        dias_desde_recepcion=60,
        cumple_condiciones=False,
        categoria="ropa",
        canal="tienda",
        es_defectuoso=True,
    )
    assert "GARANTIA_APLICABLE" in salida
    assert "Sección 7" in salida


def test_evaluar_devolucion_garantia_vencida():
    salida = evaluar_devolucion(
        dias_desde_recepcion=120,
        cumple_condiciones=True,
        categoria="ropa",
        canal="online",
        es_defectuoso=True,
    )
    assert "GARANTIA_VENCIDA" in salida
    assert "REPLANIFICACION_REQUERIDA" in salida


@pytest.mark.parametrize(
    "categoria,descuento,esperado",
    [
        ("ropa interior", 0, "NO_CAMBIABLE_CATEGORIA"),
        ("traje de baño", 0, "NO_CAMBIABLE_CATEGORIA"),
        ("ropa", 60, "NO_CAMBIABLE_DESCUENTO"),
    ],
)
def test_evaluar_devolucion_exclusiones(categoria, descuento, esperado):
    salida = evaluar_devolucion(
        dias_desde_recepcion=10,
        cumple_condiciones=True,
        categoria=categoria,
        canal="tienda",
        descuento_porcentaje=descuento,
    )
    assert esperado in salida


def test_evaluar_devolucion_sin_stock_de_reemplazo():
    salida = evaluar_devolucion(
        dias_desde_recepcion=10,
        cumple_condiciones=True,
        categoria="ropa",
        canal="online",
        stock_reemplazo=0,
    )
    assert "APROBADA_SIN_STOCK" in salida
    assert "STOCK_INSUFICIENTE" in salida


def test_evaluar_devolucion_condiciones_no_cumplidas():
    salida = evaluar_devolucion(
        dias_desde_recepcion=10, cumple_condiciones=False, categoria="ropa", canal="tienda"
    )
    assert "RECHAZADA_CONDICIONES" in salida


def test_calcular_operaciones():
    assert calcular("12990 * 2") == "12990 * 2 = 25.980"
    assert calcular("100 / 4") == "100 / 4 = 25"
    assert calcular("2 ** 10") == "2 ** 10 = 1.024"


def test_calcular_rechaza_codigo_arbitrario():
    assert "Error" in calcular("__import__('os').system('dir')")
    assert "división por cero" in calcular("1 / 0")


# --------------------------- escritura ---------------------------
def test_registrar_solicitud_crea_folio_y_persiste(entorno_temporal):
    salida = registrar_solicitud_devolucion(
        sku="urb-002",
        cliente="Camila Rojas",
        dias_desde_recepcion=12,
        motivo="Cambio de talla",
        canal="online",
        decision="APROBADA_ONLINE",
    )

    folio = re.search(r"DEV-\d{8}-\d{3}-[A-Z0-9]{4}", salida).group(0)
    assert folio.startswith("DEV-")
    assert "Camila Rojas" in salida

    datos = json.loads(config.SOLICITUDES_FILE.read_text(encoding="utf-8"))
    assert len(datos["solicitudes"]) == 1
    registro = datos["solicitudes"][0]
    assert registro["folio"] == folio
    assert registro["sku"] == "URB-002"
    assert registro["estado"] == "en_preparacion"


def test_registrar_solicitud_rechazada_queda_observada(entorno_temporal):
    salida = registrar_solicitud_devolucion(
        sku="URB-004",
        cliente="Camila Rojas",
        dias_desde_recepcion=45,
        motivo="No me gustó",
        canal="tienda",
        decision="RECHAZADA_POR_PLAZO",
    )
    assert "observada" in salida


def test_correlativo_diario(entorno_temporal):
    for i in range(2):
        registrar_solicitud_devolucion(
            sku="URB-001",
            cliente=f"Cliente {i}",
            dias_desde_recepcion=3,
            motivo="talla",
            canal="tienda",
            decision="APROBADA_TIENDA",
        )
    datos = json.loads(config.SOLICITUDES_FILE.read_text(encoding="utf-8"))
    correlativos = [s["folio"].split("-")[2] for s in datos["solicitudes"]]
    assert correlativos == ["001", "002"]


def test_registrar_nota_en_caso_existente(entorno_temporal):
    salida = registrar_solicitud_devolucion(
        sku="URB-003",
        cliente="Benjamín Rojas",
        dias_desde_recepcion=4,
        motivo="talla",
        canal="online",
        decision="APROBADA_ONLINE",
    )
    folio = re.search(r"DEV-\d{8}-\d{3}-[A-Z0-9]{4}", salida).group(0)

    nota = registrar_nota_caso(folio, "Cliente acepta nota de crédito")

    assert "Nota agregada" in nota
    assert "1 notas" in nota


def test_registrar_nota_sin_folio_es_error(entorno_temporal):
    assert "ERROR" in registrar_nota_caso("", "nota huérfana")
    assert not config.SOLICITUDES_FILE.exists()


def test_registrar_nota_con_folio_inexistente_crea_caso(entorno_temporal):
    salida = registrar_nota_caso("DEV-20260101-999-ZZZZ", "Caso abierto por teléfono")
    assert "no existe" in salida
    assert "SOLICITUD REGISTRADA" in salida


# --------------------------- consulta ---------------------------
def test_consultar_producto_por_sku():
    salida = consultar_producto("URB-001")
    assert "polera" in salida.lower()
    assert "$12990" in salida


def test_consultar_producto_por_categoria():
    salida = consultar_producto("chaqueta")
    assert "SKU:" in salida


def test_consultar_producto_inexistente_sugiere():
    salida = consultar_producto("zapatilla espacial")
    assert "No encontré productos" in salida


def test_consultar_stock_y_talla():
    salida = consultar_stock("URB-002", talla="32")
    assert "stock total" in salida
    assert "DISPONIBLE" in salida or "STOCK BAJO" in salida


def test_consultar_politica_devuelve_fuente_correcta(retriever):
    salida = consultar_politica("plazo para devoluciones", retriever)
    assert "politica_devoluciones" in salida
    assert "30 días" in salida


# --------------------------- registro ---------------------------
def test_catalogo_de_herramientas(entorno_temporal, retriever):
    gestor = GestorMemoria(largo_plazo=MemoriaLargoPlazo(ruta=entorno_temporal / "m.json"))
    planificador = Planificador(ruta=entorno_temporal / "p.json")

    herramientas = construir_herramientas(retriever, gestor, planificador, cache={})
    categorias = clasificar_herramientas(herramientas)

    assert len(herramientas) == 13
    assert set(categorias) == set(CATEGORIAS)
    assert "consultar_politica" in categorias["consulta"]
    assert "registrar_solicitud_devolucion" in categorias["escritura"]
    assert "replanificar_plan" in categorias["razonamiento"]
    assert "guardar_en_memoria" in categorias["escritura"]
