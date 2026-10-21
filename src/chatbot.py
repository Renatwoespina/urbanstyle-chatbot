"""Interfaz de línea de comandos del agente UrbanStyle 2.0.

Uso:
    python -m src.chatbot

Comandos durante la conversación:
    /ayuda     muestra la ayuda
    /plan      estado del plan activo
    /memoria   estado de la memoria (corto y largo plazo)
    /estado    herramientas, modelo y contadores
    /reset     reinicia la sesión (vacia memoria de corto plazo)
    salir      termina
"""

from __future__ import annotations

import sys

from src.agente import construir_agente

BANNER = """============================================================
  URBANSTYLE CHILE - Agente de Atención al Cliente 2.0
  Herramientas: consulta | escritura | razonamiento
  Memoria: corto plazo + largo plazo + recuperación semántica
  Escribe /ayuda para ver los comandos, 'salir' para terminar
============================================================"""

AYUDA = """Comandos:
  /ayuda    esta ayuda
  /plan     muestra el plan activo y su progreso
  /memoria  muestra el estado de la memoria
  /estado   configuración del agente
  /reset    reinicia la sesión (mantiene memoria de largo plazo)
  salir     termina la conversación

Ejemplos de casos:
  - ¿Cuánto cuesta la polera básica clásica?
  - Compré online el SKU URB-002 hace 12 días y me quedó grande, quiero cambiarlo
  - Compré el SKU URB-004 hace 45 días y quiero devolverlo
  - Llegó un producto defectuoso hace 60 días, ¿qué hago?"""


def _configurar_salida() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main() -> None:
    _configurar_salida()
    print(BANNER)
    print("\nInicializando agente (retriever + memoria + planificador)...")
    agente = construir_agente()
    print("Listo. Puedes escribir tu consulta.\n")

    while True:
        try:
            entrada = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGracias por contactar UrbanStyle. ¡Hasta pronto!")
            break

        if not entrada:
            continue
        if entrada.lower() in ("salir", "exit", "quit"):
            print("\nGracias por contactar UrbanStyle. ¡Hasta pronto!")
            break
        if entrada.lower() in ("/ayuda", "ayuda", "help"):
            print(AYUDA + "\n")
            continue
        if entrada.lower() == "/plan":
            print("\n" + agente.planificador.consultar() + "\n")
            continue
        if entrada.lower() == "/memoria":
            estado = agente.memoria.estado()
            print(f"\nMemoria: {estado}\n")
            print(agente.memoria.largo.resumen_memoria() + "\n")
            continue
        if entrada.lower() == "/estado":
            print(f"\n{agente.estado()}\n")
            continue
        if entrada.lower() == "/reset":
            print("\n" + agente.reiniciar_sesion() + "\n")
            continue

        try:
            resultado = agente.preguntar(entrada)
        except Exception as exc:
            print(f"\nUrbanBot: No pude completar la consulta por un problema técnico ({exc}).")
            print("Puedes contactar a soporte@urbanstyle.cl o al 600-URBAN-STYLE.\n")
            continue

        print(f"\nUrbanBot: {resultado['respuesta']}\n")
        usadas = resultado.get("herramientas_usadas", [])
        if usadas:
            print(f"  [herramientas: {', '.join(usadas)}]")
        plan = resultado.get("plan", {})
        if plan.get("activo"):
            print(
                f"  [plan v{plan['version']} · {plan['progreso']}% · "
                f"replanificaciones: {plan['replanificaciones']}]"
            )
        print()


if __name__ == "__main__":
    main()
