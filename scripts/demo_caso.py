"""Demo end-to-end del agente UrbanStyle 2.0.

Ejecuta escenarios del caso organizacional (atención al cliente + gestión de
devoluciones) mostrando la traza de herramientas, el plan y la memoria, y deja
evidencia en docs/.

Uso:
    python -m scripts.demo_caso                 # todos los escenarios
    python -m scripts.demo_caso --limpio        # borra datos generados y ejecuta todo
    python -m scripts.demo_caso -e 2            # sólo el escenario 2 (útil en la defensa)
    python -m scripts.demo_caso -e 1,2,3        # varios escenarios
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from src import config
from src.agente import AgenteUrbanStyle, construir_agente

ESCENARIOS: dict[int, dict] = {
    1: {
        "titulo": "Consulta simple (herramienta de consulta, sin planificación)",
        "entrada": "Hola, ¿cuánto cuesta la polera básica clásica y cuántas unidades tienen en stock?",
        "esperado": "El agente usa consultar_producto/consultar_stock y responde sin crear un plan.",
        "nueva_sesion": True,
    },
    2: {
        "titulo": "Devolución dentro de plazo (plan completo + escritura)",
        "entrada": (
            "Hola, soy Camila Rojas. Compré online el SKU URB-002 hace 12 días y me quedó grande. "
            "Quiero cambiarlo por la talla 32. ¿Se puede?"
        ),
        "esperado": "Planifica, evalúa la política, registra la solicitud con folio y guarda el caso en memoria.",
        "nueva_sesion": False,
    },
    3: {
        "titulo": "Condición cambiante: plazo vencido (replanificación)",
        "entrada": (
            "Soy Camila Rojas de nuevo. Compré el SKU URB-004 en tienda hace 45 días y quiero "
            "devolverlo porque no me gustó. ¿Me devuelven la plata?"
        ),
        "esperado": "evaluar_devolucion devuelve RECHAZADA_POR_PLAZO y el agente llama replanificar_plan (plan v2).",
        "nueva_sesion": False,
    },
    4: {
        "titulo": "Condición cambiante: producto defectuoso fuera del plazo de 30 días",
        "entrada": (
            "Hola, recibí el SKU URB-005 hace 60 días y la costura se abrió al segundo uso. "
            "¿Puedo hacer algo aunque ya pasó el mes?"
        ),
        "esperado": "El motor de reglas aplica la garantía de 90 días (Sección 7) y no el plazo de 30.",
        "nueva_sesion": False,
    },
    5: {
        "titulo": "Continuidad de memoria entre sesiones",
        "entrada": "Hola, soy Camila Rojas. ¿Recuerdas el caso que abrí la vez pasada?",
        "esperado": "El agente recupera de la memoria de largo plazo el folio y los datos del caso anterior.",
        "nueva_sesion": True,
    },
}


def _seleccionar(rango: str | None) -> list[int]:
    if not rango:
        return sorted(ESCENARIOS)
    ids: list[int] = []
    for parte in rango.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = parte.split("-")
            ids.extend(range(int(a), int(b) + 1))
        else:
            ids.append(int(parte))
    return [i for i in ids if i in ESCENARIOS]


def limpiar_datos() -> None:
    for ruta in (config.MEMORIA_FILE, config.SOLICITUDES_FILE, config.PLAN_FILE):
        if ruta.exists():
            ruta.unlink()
    print("[demo] datos generados eliminados (memoria, solicitudes, plan)\n")


def mostrar(resultado: dict) -> None:
    print("TRAZA DE HERRAMIENTAS")
    if not resultado.get("traza"):
        print("  (el agente respondió sin herramientas)")
    for i, paso in enumerate(resultado["traza"], 1):
        print(f"  {i:02d}. {paso['accion']}({paso['entrada']})")
        obs = str(paso["observacion"]).replace("\n", "\n      ")
        print(f"      -> {obs[:420]}{'...' if len(obs) > 420 else ''}")
    print("\nRESPUESTA AL CLIENTE")
    for linea in resultado["respuesta"].splitlines():
        print("  " + linea)
    print("\nESTADO")
    print(f"  plan:    {resultado['plan']}")
    print(f"  memoria: {resultado['memoria']}")
    print()


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Demo del agente UrbanStyle 2.0")
    parser.add_argument("-e", "--escenarios", help="ids de escenario, ej: 1,2-4")
    parser.add_argument("--limpio", action="store_true", help="borra memoria/solicitudes/plan antes de ejecutar")
    parser.add_argument(
        "--acumular",
        action="store_true",
        help="conserva los escenarios ya registrados en la evidencia (útil para corridas parciales por cuota)",
    )
    parser.add_argument("--sin-supervision", action="store_true", help="omite la reflexión final del supervisor")
    args = parser.parse_args()

    if args.limpio:
        limpiar_datos()

    ids = _seleccionar(args.escenarios)
    agente: AgenteUrbanStyle | None = None
    evidencias: list[dict] = []
    ruta_json = config.DOCS_DIR / "evidencia_demo.json"

    if args.acumular and ruta_json.exists():
        try:
            with open(ruta_json, encoding="utf-8") as fh:
                evidencias = json.load(fh)
            print(f"[demo] evidencia previa cargada: {len(evidencias)} escenario(s)\n")
        except Exception:  # noqa: BLE001 - evidencia corrupta se reemplaza
            evidencias = []

    for numero in ids:
        escenario = ESCENARIOS[numero]
        print("=" * 78)
        print(f"ESCENARIO {numero}: {escenario['titulo']}")
        print("=" * 78)
        print(f"Cliente: {escenario['entrada']}")
        print(f"Esperado: {escenario['esperado']}\n")

        if agente is None or escenario["nueva_sesion"]:
            agente = construir_agente()
            print("[demo] sesión iniciada: memoria de corto plazo vacía; largo plazo recargada desde disco\n")

        try:
            resultado = agente.preguntar(escenario["entrada"])
            mostrar(resultado)

            if not args.sin_supervision:
                print("SUPERVISIÓN (reflexión sobre la traza)")
                print("  " + agente.supervisar(resultado).replace("\n", "\n  "))
                print()

            evidencias.append(
                {
                    "escenario": numero,
                    "titulo": escenario["titulo"],
                    "entrada": escenario["entrada"],
                    "herramientas": resultado["herramientas_usadas"],
                    "traza": resultado["traza"],
                    "respuesta": resultado["respuesta"],
                    "plan": resultado["plan"],
                    "memoria": resultado["memoria"],
                    "modelo": config.MODEL,
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                }
            )
        except Exception as exc:  # noqa: BLE001 - un escenario no aborta la corrida
            print(f"[demo] ERROR en el escenario {numero}: {type(exc).__name__}: {exc}\n")
            evidencias.append(
                {
                    "escenario": numero,
                    "titulo": escenario["titulo"],
                    "entrada": escenario["entrada"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "modelo": config.MODEL,
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                }
            )
            # Nueva sesión limpia para no arrastrar estado de un turno fallido.
            agente = construir_agente()

    config.asegurar_directorios()

    if args.acumular:
        # Un escenario re-ejecutado: se conserva el último registro exitoso y,
        # si no lo hubo, el último intento (incluso si falló).
        por_id: dict[int, dict] = {}
        for e in evidencias:
            previo = por_id.get(e["escenario"])
            if previo is None:
                por_id[e["escenario"]] = e
            elif previo.get("error") and not e.get("error"):
                por_id[e["escenario"]] = e
            elif not previo.get("error") and e.get("error"):
                pass
            else:
                por_id[e["escenario"]] = e
        evidencias = [por_id[k] for k in sorted(por_id)]

    texto = []
    for e in evidencias:
        texto.append(f"ESCENARIO {e['escenario']}: {e['titulo']}")
        texto.append(f"Fecha: {e['fecha']}")
        texto.append(f"Modelo: {e.get('modelo', 'n/d')}")
        texto.append(f"Entrada: {e['entrada']}")
        if e.get("error"):
            texto.append(f"ERROR: {e['error']}")
            texto.append("")
            continue
        texto.append(f"Herramientas: {', '.join(e['herramientas']) or '(ninguna)'}")
        for i, p in enumerate(e["traza"], 1):
            texto.append(f"  {i}. {p['accion']}({p['entrada']}) -> {str(p['observacion'])[:500]}")
        texto.append(f"Respuesta: {e['respuesta']}")
        texto.append(f"Plan: {e['plan']}")
        texto.append(f"Memoria: {e['memoria']}")
        texto.append("")

    ruta_txt = config.DOCS_DIR / "evidencia_pruebas.txt"
    modelos = sorted({e.get("modelo", "n/d") for e in evidencias})
    with open(ruta_txt, "w", encoding="utf-8") as fh:
        fh.write("EVIDENCIA DE EJECUCIÓN - AGENTE URBANSTYLE 2.0\n")
        fh.write(f"Generado: {datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"Modelos usados: {', '.join(modelos)}\n\n")
        fh.write("\n".join(texto))

    ruta_json = config.DOCS_DIR / "evidencia_demo.json"
    with open(ruta_json, "w", encoding="utf-8") as fh:
        json.dump(evidencias, fh, ensure_ascii=False, indent=2)

    print(f"Evidencia escrita en {ruta_txt}")
    print(f"Evidencia JSON en {ruta_json}")


if __name__ == "__main__":
    main()
