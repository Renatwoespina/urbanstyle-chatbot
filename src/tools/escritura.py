"""Herramientas de **escritura** del agente UrbanStyle 2.0.

Son las únicas herramientas capaces de modificar el estado del sistema:

- `registrar_solicitud_devolucion`: persiste una solicitud en `data/solicitudes.json`.
- `registrar_nota_caso`: agrega notas de seguimiento a una solicitud existente.
- `guardar_en_memoria`: escribe hechos, preferencias o casos en la memoria de
  largo plazo (`data/memoria.json`), que luego se recuperan semánticamente.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from langchain_core.tools import StructuredTool

from src import config

ESTADOS_SOLICITUD = ("registrada", "en_preparacion", "cerrada", "observada")


def _leer_solicitudes() -> list[dict]:
    if not config.SOLICITUDES_FILE.exists():
        return []
    with open(config.SOLICITUDES_FILE, encoding="utf-8") as fh:
        return json.load(fh).get("solicitudes", [])


def _escribir_solicitudes(registros: list[dict]) -> None:
    with open(config.SOLICITUDES_FILE, "w", encoding="utf-8") as fh:
        json.dump(
            {"actualizado": datetime.now().isoformat(timespec="seconds"), "solicitudes": registros},
            fh,
            ensure_ascii=False,
            indent=2,
        )


def registrar_solicitud_devolucion(
    sku: str,
    cliente: str,
    dias_desde_recepcion: int,
    motivo: str,
    canal: str,
    decision: str,
    monto_clp: int = 0,
    notas: str = "",
) -> str:
    """Crea una solicitud de cambio/devolución con ID correlativo y la persiste en disco.

    `decision` debe ser la resolución que entregó `evaluar_devolucion`
    (p. ej. APROBADA_TIENDA, APROBADA_ONLINE, GARANTIA_APLICABLE, RECHAZADA_POR_PLAZO).
    """
    solicitudes = _leer_solicitudes()
    fecha = datetime.now()
    correlativo = len([s for s in solicitudes if s["fecha"][:10] == fecha.strftime("%Y-%m-%d")]) + 1
    folio = f"DEV-{fecha.strftime('%Y%m%d')}-{correlativo:03d}-{uuid.uuid4().hex[:4].upper()}"
    registro = {
        "folio": folio,
        "sku": sku.strip().upper(),
        "cliente": cliente.strip(),
        "dias_desde_recepcion": int(dias_desde_recepcion),
        "motivo": motivo.strip(),
        "canal": canal.strip().lower(),
        "decision": decision.strip().upper(),
        "monto_clp": int(monto_clp),
        "estado": "en_preparacion" if str(decision).upper().startswith(("APROBADA", "GARANTIA")) else "observada",
        "notas": [notas.strip()] if notas.strip() else [],
        "fecha": fecha.isoformat(timespec="seconds"),
    }
    solicitudes.append(registro)
    _escribir_solicitudes(solicitudes)
    return (
        f"SOLICITUD REGISTRADA - folio {folio}\n"
        f"  Cliente: {registro['cliente']} | SKU: {registro['sku']} | Canal: {registro['canal']}\n"
        f"  Días desde recepción: {registro['dias_desde_recepcion']} | Decisión: {registro['decision']}\n"
        f"  Monto: ${registro['monto_clp']} CLP | Estado: {registro['estado']}\n"
        "Este folio debe entregarse al cliente como comprobante del caso."
    )


def registrar_nota_caso(folio: str, nota: str) -> str:
    """Agrega una nota de seguimiento a una solicitud. Si el folio no existe, la crea como caso abierto."""
    solicitudes = _leer_solicitudes()
    nota = nota.strip()
    if not nota:
        return "La nota está vacía."
    if not folio.strip():
        return (
            "ERROR: falta el folio. No se creó ningún caso. Si la solicitud aún no existe, "
            "usa primero `registrar_solicitud_devolucion` y luego anota el folio devuelto."
        )
    for s in solicitudes:
        if s["folio"].upper() == folio.strip().upper():
            s.setdefault("notas", []).append(nota)
            _escribir_solicitudes(solicitudes)
            return f"Nota agregada a {s['folio']} ({len(s['notas'])} notas). Estado: {s['estado']}"
    folio_nuevo = registrar_solicitud_devolucion(
        sku="SIN-SKU",
        cliente="sin especificar",
        dias_desde_recepcion=0,
        motivo="caso abierto por nota de seguimiento",
        canal="interno",
        decision="OBSERVADA",
        notas=nota,
    )
    return (
        f"El folio '{folio}' no existe; se creó un caso interno con la nota.\n{folio_nuevo}"
    )


def construir_herramientas_escritura(gestor_memoria) -> list:
    def guardar_en_memoria(contenido: str, tipo: str = "hecho") -> str:
        """Escribe un recuerdo en la memoria de largo plazo del agente.

        Úsala para datos que deban recordarse en futuras sesiones: nombre del
        cliente, número de pedido, acuerdo entregado o preferencias.
        """
        return _guardar_en_memoria(gestor_memoria, contenido, tipo)

    return [
        StructuredTool.from_function(
            func=registrar_solicitud_devolucion,
            name="registrar_solicitud_devolucion",
            description=(
                "Persiste una solicitud de cambio/devolución en data/solicitudes.json con folio "
                "correlativo. El campo 'decision' debe ser EXACTAMENTE el valor devuelto por "
                "`evaluar_devolucion` (p. ej. APROBADA_ONLINE, APROBADA_TIENDA, GARANTIA_APLICABLE). "
                "Úsala SIEMPRE que una evaluación quede aprobada o deba quedar registrada."
            ),
            tags=["escritura"],
        ),
        StructuredTool.from_function(
            func=registrar_nota_caso,
            name="registrar_nota_caso",
            description=(
                "Agrega una nota de seguimiento a una solicitud existente por folio. "
                "Úsala para documentar acuerdos, alternativas ofrecidas o escalamientos."
            ),
            tags=["escritura"],
        ),
        StructuredTool.from_function(
            func=guardar_en_memoria,
            name="guardar_en_memoria",
            description=(
                "Escribe un recuerdo en la memoria de largo plazo del agente (hecho, preferencia, "
                "caso o contacto). Úsala para datos que deban recordarse en futuras sesiones: "
                "nombre del cliente, número de pedido, acuerdo entregado, etc."
            ),
            tags=["escritura", "memoria"],
        ),
    ]


def _guardar_en_memoria(gestor_memoria, contenido: str, tipo: str = "hecho") -> str:
    tipos_validos = ("hecho", "preferencia", "caso", "contacto", "resumen")
    tipo = tipo if tipo in tipos_validos else "hecho"
    registro = gestor_memoria.recordar(contenido, tipo=tipo, metadata={"origen": "herramienta"})
    return (
        f"Recuerdo {registro.id} guardado en memoria de largo plazo "
        f"(tipo: {tipo}, {len(contenido)} caracteres)."
    )
