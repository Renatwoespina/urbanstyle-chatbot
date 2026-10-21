"""Procesos de memoria del agente UrbanStyle 2.0.

Se implementan tres mecanismos diferenciados (IL2.2 / IE3 / IE4):

1. **Memoria de corto plazo**: ventana deslizante de mensajes de la conversación
   actual (`MEMORIA_FILE` no interviene aquí, es volátil por sesión).
2. **Compresión / resumen**: cuando la ventana supera `TURNO_PARA_RESUMEN`
   mensajes, el LLM genera un resumen que se conserva y se envía al largo plazo,
   evitando perder el contexto de flujos prolongados.
3. **Memoria de largo plazo**: almacén persistente en JSON (`memoria.json`) con
   hechos, preferencias, casos y resúmenes, recuperado **semánticamente** con un
   índice TF-IDF (similitud coseno) sobre los propios recuerdos.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sklearn.feature_extraction.text import TfidfVectorizer

from src import config
from src.texto import analizador


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


_FOLIO_RE = re.compile(r"(DEV-\d{8}-\d{3}-[A-Z0-9]{4})")


class Registro:
    """Un recuerdos persistente del agente."""

    def __init__(
        self,
        contenido: str,
        tipo: str = "hecho",
        metadata: dict | None = None,
        registro_id: str | None = None,
        fecha: str | None = None,
    ):
        self.id = registro_id or uuid.uuid4().hex[:8]
        self.tipo = tipo
        self.contenido = contenido
        self.metadata = metadata or {}
        self.fecha = fecha or _ahora()

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "contenido": self.contenido,
            "metadata": self.metadata,
            "fecha": self.fecha,
        }

    @classmethod
    def desde_dict(cls, data: dict) -> "Registro":
        return cls(
            contenido=data["contenido"],
            tipo=data.get("tipo", "hecho"),
            metadata=data.get("metadata", {}),
            registro_id=data.get("id"),
            fecha=data.get("fecha"),
        )

    def __repr__(self) -> str:
        return f"Registro({self.id}, {self.tipo}, {len(self.contenido)} chars)"


class MemoriaLargoPlazo:
    """Almacén persistente de recuerdos con recuperación semántica (TF-IDF)."""

    def __init__(self, ruta=config.MEMORIA_FILE):
        self.ruta = ruta
        self._lock = threading.Lock()
        self._registros: list[Registro] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._vectors = None
        self._indice_sucio = True
        self.cargar()

    # --- persistencia ---
    def cargar(self) -> None:
        if not self.ruta.exists():
            self._registros = []
            return
        with open(self.ruta, encoding="utf-8") as fh:
            data = json.load(fh)
        self._registros = [Registro.desde_dict(r) for r in data.get("registros", [])]
        self._indice_sucio = True

    def guardar(self) -> None:
        with open(self.ruta, "w", encoding="utf-8") as fh:
            json.dump(
                {"actualizado": _ahora(), "registros": [r.a_dict() for r in self._registros]},
                fh,
                ensure_ascii=False,
                indent=2,
            )

    # --- escritura (IE3) ---
    def agregar(self, contenido: str, tipo: str = "hecho", metadata: dict | None = None) -> Registro:
        registro = Registro(contenido=contenido, tipo=tipo, metadata=metadata)
        with self._lock:
            self._registros.append(registro)
            self._indice_sucio = True
            self.guardar()
        return registro

    def listar(self, tipo: str | None = None) -> list[Registro]:
        if tipo is None:
            return list(self._registros)
        return [r for r in self._registros if r.tipo == tipo]

    def olvidar(self, registro_id: str) -> bool:
        with self._lock:
            antes = len(self._registros)
            self._registros = [r for r in self._registros if r.id != registro_id]
            if len(self._registros) != antes:
                self._indice_sucio = True
                self.guardar()
                return True
        return False

    def limpiar(self) -> None:
        with self._lock:
            self._registros = []
            self._indice_sucio = True
            self.guardar()

    # --- recuperación de contexto semántico (IE4) ---
    def _construir_indice(self) -> None:
        if not self._indice_sucio and self._vectorizer is not None:
            return
        if not self._registros:
            self._vectorizer = None
            self._vectors = None
            self._indice_sucio = False
            return
        textos = [f"{r.tipo}: {r.contenido}" for r in self._registros]
        self._vectorizer = TfidfVectorizer(analyzer=analizador)
        self._vectors = self._vectorizer.fit_transform(textos)
        self._indice_sucio = False

    def buscar_semantica(self, consulta: str, k: int = config.RECUPERACION_SEMANTICA_K) -> list[Registro]:
        """Recupera los recuerdos más afines a la consulta por similitud coseno."""
        if not self._registros or not consulta.strip():
            return []
        with self._lock:
            self._construir_indice()
            if self._vectorizer is None:
                return []
            q = self._vectorizer.transform([consulta])
            import numpy as np

            scores = np.asarray((q @ self._vectors.T).todense()).flatten()
            orden = scores.argsort()[::-1][:k]
            return [self._registros[int(i)] for i in orden if scores[int(i)] > 0]

    def resumen_memoria(self) -> str:
        if not self._registros:
            return "(memoria de largo plazo vacía)"
        lineas = []
        for r in self._registros[-12:]:
            lineas.append(f"- [{r.tipo}] {r.contenido}")
        return "\n".join(lineas)


class MemoriaCortoPlazo:
    """Ventana deslizante de la conversación + resumen comprimido."""

    def __init__(self, ventana: int = config.VENTANA_CORTO_PLAZO):
        self.ventana = ventana
        self.mensajes: list[BaseMessage] = []
        self.resumen: str = ""

    def agregar(self, mensaje: BaseMessage) -> None:
        self.mensajes.append(mensaje)

    def registrar_turno(self, pregunta: str, respuesta: str) -> None:
        self.mensajes.append(HumanMessage(content=pregunta))
        self.mensajes.append(AIMessage(content=respuesta))

    def ventana_actual(self) -> list[BaseMessage]:
        if len(self.mensajes) <= self.ventana:
            return list(self.mensajes)
        return list(self.mensajes[-self.ventana :])

    def excede(self) -> bool:
        return len(self.mensajes) >= config.TURNO_PARA_RESUMEN

    def comprimir(self, llm) -> str:
        """Resume el historial y lo reemplaza por el resumen (libera ventana).

        El resumen generado se devuelve para que el gestor lo persista en la
        memoria de largo plazo: así la continuidad sobrevive al recorte.
        """
        transcripcion = "\n".join(
            f"{type(m).__name__}: {m.content}" for m in self.mensajes
        )
        prompt = (
            "Resume en máximo 120 palabras, en español y sin inventar datos, "
            "la conversación de atención al cliente. Conserva: nombre o datos del "
            "cliente, productos consultados, montos, plazos, decisiones tomadas y "
            "pendientes abiertos.\n\nCONVERSACIÓN:\n" + transcripcion
        )
        try:
            salida = llm.invoke(prompt)
            self.resumen = getattr(salida, "content", str(salida)) or self.resumen
        except Exception as exc:  # pragma: no cover - red opcional en tests
            self.resumen = self.resumen or f"(resumen no disponible: {exc})"
        # Se conserva el resumen + los últimos 4 mensajes para no perder el hilo.
        self.mensajes = [AIMessage(content=f"[Resumen previo] {self.resumen}")] + list(
            self.mensajes[-4:]
        )
        return self.resumen


class GestorMemoria:
    """Orquesta corto plazo, compresión y recuperación semántica por turno."""

    def __init__(self, llm=None, largo_plazo: MemoriaLargoPlazo | None = None):
        self.llm = llm
        self.corto = MemoriaCortoPlazo()
        self.largo = largo_plazo or MemoriaLargoPlazo()

    def registrar_turno(self, pregunta: str, respuesta: str) -> None:
        self.corto.registrar_turno(pregunta, respuesta)
        if self.corto.excede() and self.llm is not None:
            resumen = self.corto.comprimir(self.llm)
            self.largo.agregar(
                f"Resumen de conversación: {resumen}",
                tipo="resumen",
                metadata={"origen": "compresion_corto_plazo"},
            )

    def recordar(self, contenido: str, tipo: str = "hecho", metadata: dict | None = None) -> Registro:
        """Escritura explícita en memoria de largo plazo (herramienta `guardar_en_memoria`)."""
        return self.largo.agregar(contenido, tipo=tipo, metadata=metadata)

    def recuperar(self, consulta: str) -> list[Registro]:
        return self.largo.buscar_semantica(consulta)

    def consolidar_traza(self, traza: list[dict]) -> list[Registro]:
        """Consolida en largo plazo los casos registrados durante el turno.

        Esta consolidación es determinista (no depende de que el LLM decida
        llamar a `guardar_en_memoria`), lo que garantiza la continuidad del caso
        entre sesiones.
        """
        nuevos: list[Registro] = []
        for paso in traza or []:
            if paso.get("accion") != "registrar_solicitud_devolucion":
                continue
            observacion = str(paso.get("observacion", ""))
            coincidencia = _FOLIO_RE.search(observacion)
            folio = coincidencia.group(1) if coincidencia else "(sin folio)"
            datos = paso.get("entrada", {}) or {}
            contenido = (
                f"Caso {folio} - cliente {datos.get('cliente', 'n/d')} - "
                f"SKU {datos.get('sku', 'n/d')} - motivo: {datos.get('motivo', 'n/d')} - "
                f"decisión {datos.get('decision', 'n/d')} - "
                f"{datos.get('dias_desde_recepcion', 'n/d')} días desde recepción - "
                f"canal {datos.get('canal', 'n/d')}"
            )
            nuevos.append(self.recordar(contenido, tipo="caso", metadata={"folio": folio}))
        return nuevos

    def bloque_contexto(self, consulta: str) -> str:
        """Bloque de memoria que sólo incluye largo plazo + resumen (para el prompt del sistema)."""
        return self.bloque_largo_plazo(consulta)

    def bloque_largo_plazo(self, consulta: str) -> str:
        """Recuerdos relevantes + resumen comprimido, sin los turnos crudos."""
        partes: list[str] = []
        recuerdos = self.recuperar(consulta)
        etiqueta = "recuerdos relevantes"
        if not recuerdos:
            # Sin coincidencias semánticas se ofrecen los últimos recuerdos como contexto mínimo.
            recuerdos = self.largo.listar()[-2:]
            etiqueta = "últimos recuerdos"
        if recuerdos:
            bloque = "\n".join(
                f"- ({r.tipo}, {r.fecha}) {r.contenido}" for r in recuerdos
            )
            partes.append(f"[MEMORIA DE LARGO PLAZO - {etiqueta}]\n{bloque}")
        if self.corto.resumen:
            partes.append(f"[RESUMEN DE LA CONVERSACIÓN]\n{self.corto.resumen}")
        if not partes:
            return "[MEMORIA] Sin interacciones previas registradas."
        return "\n\n".join(partes)

    def ventana_mensajes(self) -> list[BaseMessage]:
        """Ventana deslizante de corto plazo como mensajes reales (para chat_history)."""
        return self.corto.ventana_actual()

    def bloque_completo(self, consulta: str) -> str:
        """Versión de texto plano con largo plazo, resumen y últimos turnos."""
        partes = [self.bloque_largo_plazo(consulta)]
        ventana = self.corto.ventana_actual()
        if ventana:
            lineas = [f"- {type(m).__name__}: {m.content}" for m in ventana]
            partes.append("[ÚLTIMOS TURNOS - memoria de corto plazo]\n" + "\n".join(lineas))
        return "\n\n".join(p for p in partes if p)

    def estado(self) -> dict[str, Any]:
        return {
            "turnos_corto_plazo": len(self.corto.mensajes),
            "ventana": self.corto.ventana,
            "resumen_activo": bool(self.corto.resumen),
            "recuerdos_largo_plazo": len(self.largo.listar()),
            "por_tipo": {
                t: len(self.largo.listar(t))
                for t in sorted({r.tipo for r in self.largo.listar()})
            }
            or {},
        }
