"""Orquestación del agente UrbanStyle 2.0 (IL2.1 / IL2.4 / IE1, IE2).

Aquí se ensamblan los cuatro componentes de la arquitectura:

    usuario -> GestorMemoria (corto/largo plazo + recuperación semántica)
             -> Prompt de sistema con memoria inyectada
             -> AgentExecutor de LangChain (loop de razonamiento con herramientas)
             -> Herramientas {consulta, escritura, razonamiento/planificación}
             -> Planificador (plan priorizado y replanificable)
             -> respuesta + traza persistida
"""

from __future__ import annotations

import re

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from src import config
from src.memoria import GestorMemoria, MemoriaLargoPlazo
from src.planificador import Planificador
from src.prompts import AGENTE_HUMANO, AGENTE_SISTEMA, REFLEXION_FINAL
from src.rag_pipeline import crear_retriever, invocar_llm
from src.tools import clasificar_herramientas, construir_herramientas

_FOLIO_RE = re.compile(r"(DEV-\d{8}-\d{3}-[A-Z0-9]{4})")

#: Mensajes que devuelve AgentExecutor al agotar el presupuesto de iteraciones.
MENSAJES_DE_CORTE = {
    "Agent stopped due to iteration limit or time limit.",
    "Agent stopped due to max iterations.",
}


def crear_llm(model: str | None = None, temperatura: float | None = None) -> ChatGroq:
    config.cargar_entorno()
    return ChatGroq(
        model=model or config.MODEL,
        temperature=config.TEMPERATURE if temperatura is None else temperatura,
        max_tokens=config.MAX_TOKENS,
        max_retries=config.MAX_REINTENTOS_LLM,
        model_kwargs={"reasoning_effort": config.REASONING_EFFORT},
    )


def construir_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", AGENTE_SISTEMA),
            MessagesPlaceholder("chat_history"),
            ("human", AGENTE_HUMANO),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )


class AgenteUrbanStyle:
    """Agente funcional de atención al cliente con memoria y planificación."""

    def __init__(self, llm=None, verbose: bool = False, ruta_memoria=None, ruta_plan=None):
        config.cargar_entorno()
        config.asegurar_directorios()

        self.llm = llm or crear_llm()
        self.retriever = crear_retriever()
        self.memoria = GestorMemoria(
            llm=self.llm,
            largo_plazo=MemoriaLargoPlazo(ruta=ruta_memoria or config.MEMORIA_FILE),
        )
        self.planificador = Planificador(llm=self.llm, ruta=ruta_plan or config.PLAN_FILE)
        self.cache_evidencias: dict = {}
        self.herramientas = construir_herramientas(
            retriever=self.retriever,
            gestor_memoria=self.memoria,
            planificador=self.planificador,
            cache=self.cache_evidencias,
        )
        self.categorias = clasificar_herramientas(self.herramientas)
        self.prompt = construir_prompt()
        self.agente = create_tool_calling_agent(self.llm, self.herramientas, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agente,
            tools=self.herramientas,
            max_iterations=config.MAX_ITERACIONES,
            max_execution_time=240,
            early_stopping_method="force",
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            verbose=verbose,
        )

    # ------------------------------------------------------------------
    def _snapshot(self) -> dict:
        """Copia los archivos que la ejecución de un turno puede modificar."""
        datos = {}
        for ruta in (config.SOLICITUDES_FILE, config.MEMORIA_FILE, config.PLAN_FILE):
            try:
                datos[ruta] = ruta.read_bytes()
            except FileNotFoundError:
                datos[ruta] = None
        return datos

    def _restaurar(self, snapshot: dict) -> None:
        for ruta, contenido in snapshot.items():
            if contenido is None:
                ruta.unlink(missing_ok=True)
            else:
                ruta.write_bytes(contenido)

    def preguntar(self, entrada: str) -> dict:
        """Ejecuta un turno completo del agente y devuelve respuesta, traza y estados.

        El turno es **atómico**: si el proveedor falla a mitad de la ejecución
        (p. ej. invocación de herramienta mal formada), los archivos de escritura
        vuelven al estado anterior y el turno se reintenta una vez. Así un fallo
        de red o del modelo no deja solicitudes o planes a medio crear.
        """
        entrada = entrada.strip()
        if not entrada:
            return {"respuesta": "", "traza": [], "plan": self.planificador.estado(), "memoria": self.memoria.estado()}

        self.cache_evidencias.clear()
        bloque_memoria = self.memoria.bloque_largo_plazo(entrada)
        ventana = self.memoria.ventana_mensajes()
        snapshot = self._snapshot()

        for intento in range(2):
            try:
                salida = self.executor.invoke(
                    {
                        "input": entrada,
                        "memoria": bloque_memoria,
                        "chat_history": ventana,
                    }
                )
                break
            except Exception:
                self._restaurar(snapshot)
                self.planificador.cargar()
                if intento == 1:
                    raise
                # Reintento con muestreo distinto: fallas deterministas del proveedor
                # (nombre de herramienta mal formado) no se repiten al variar la
                # temperatura.
                self.llm.temperature = 0.3

        respuesta = salida.get("output", "").strip()
        traza = self._formatear_traza(salida.get("intermediate_steps", []))
        if respuesta in MENSAJES_DE_CORTE:
            respuesta = self._respuesta_de_corte(traza)

        self.memoria.registrar_turno(entrada, respuesta)
        nuevos_recuerdos = self.memoria.consolidar_traza(traza)

        return {
            "entrada": entrada,
            "respuesta": respuesta,
            "traza": traza,
            "plan": self.planificador.estado(),
            "memoria": self.memoria.estado(),
            "herramientas_usadas": [p["accion"] for p in traza],
            "recuerdos_nuevos": [r.contenido for r in nuevos_recuerdos],
        }

    @staticmethod
    def _respuesta_de_corte(traza: list[dict]) -> str:
        """Respuesta en español cuando se agota el presupuesto de iteraciones."""
        folio = ""
        for paso in reversed(traza):
            coincidencia = _FOLIO_RE.search(str(paso.get("observacion", "")))
            if coincidencia:
                folio = coincidencia.group(1)
                break
        base = (
            "No pude completar todas las etapas del flujo dentro del presupuesto de "
            "iteraciones, pero conservo la evidencia recogida y lo ya registrado."
        )
        if folio:
            base += f" Tu caso quedó registrado con el folio {folio}."
        return (
            base
            + " Para que un ejecutive continúe el trámite, escríbenos a "
            "soporte@urbanstyle.cl o al 600-URBAN-STYLE indicando tu número de pedido."
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _formatear_traza(pasos) -> list[dict]:
        traza = []
        for accion, observacion in pasos:
            traza.append(
                {
                    "accion": getattr(accion, "tool", str(accion)),
                    "entrada": dict(getattr(accion, "tool_input", {}) or {}),
                    "observacion": str(observacion)[:900],
                }
            )
        return traza

    def supervisar(self, resultado: dict) -> str:
        """Revisión de calidad sobre la traza (razonamiento/reflexión del flujo)."""
        traza_txt = "\n".join(
            f"{i}. {p['accion']}({p['entrada']}) -> {p['observacion'][:200]}"
            for i, p in enumerate(resultado.get("traza", []), 1)
        ) or "(sin llamadas a herramientas)"
        user = (
            f"ENTRADA: {resultado.get('entrada', '')}\n"
            f"TRAZA DE HERRAMIENTAS:\n{traza_txt}\n"
            f"RESPUESTA FINAL: {resultado.get('respuesta', '')}"
        )
        try:
            return invocar_llm(REFLEXION_FINAL, user)
        except Exception as exc:  # pragma: no cover
            return f"(supervisión no disponible: {exc})"

    # ------------------------------------------------------------------
    def reiniciar_sesion(self) -> str:
        """Borra la memoria de corto plazo (nueva sesión). Conserva largo plazo y plan."""
        self.memoria.corto = type(self.memoria.corto)()
        return "Sesión reiniciada: memoria de corto plazo vaciada. Largo plazo y plan conservados."

    def estado(self) -> dict:
        return {
            "modelo": config.MODEL,
            "herramientas": self.categorias,
            "total_herramientas": len(self.herramientas),
            "memoria": self.memoria.estado(),
            "plan": self.planificador.estado(),
        }

    def transcript(self, resultado: dict) -> str:
        """Traza legible para evidencia (docs/evidencia_pruebas.txt)."""
        lineas = [f"ENTRADA: {resultado.get('entrada', '')}"]
        for i, p in enumerate(resultado.get("traza", []), 1):
            lineas.append(f"  {i}. TOOL {p['accion']}({p['entrada']})")
            obs = p["observacion"].replace("\n", "\n       ")
            lineas.append(f"     OBS: {obs}")
        lineas.append(f"RESPUESTA: {resultado.get('respuesta', '')}")
        lineas.append(f"PLAN: {resultado.get('plan')}")
        lineas.append(f"MEMORIA: {resultado.get('memoria')}")
        return "\n".join(lineas)


def construir_agente(verbose: bool = False) -> AgenteUrbanStyle:
    """Punto de entrada habitual: `agente = construir_agente()`."""
    return AgenteUrbanStyle(verbose=verbose)
