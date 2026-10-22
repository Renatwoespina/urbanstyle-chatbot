"""Genera el informe técnico EP2 (máx. 5 páginas) en formato Word.

Salida: docs/Informe_EP2_UrbanStyle.docx

Uso:
    python -m scripts.generar_informe
"""

from __future__ import annotations

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from src import config

AZUL = RGBColor(0x1F, 0x3B, 0x57)
GRIS = RGBColor(0x37, 0x41, 0x51)
FUENTE = "Calibri"
TAM = 10


def _configurar_estilos(doc: Document) -> None:
    estilo = doc.styles["Normal"]
    estilo.font.name = FUENTE
    estilo.font.size = Pt(TAM)
    estilo.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    estilo.paragraph_format.space_after = Pt(4)
    estilo.paragraph_format.line_spacing = 1.05
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)

    for nivel, tam in ((1, 12), (2, 10.5)):
        h = doc.styles[f"Heading {nivel}"]
        h.font.name = FUENTE
        h.font.size = Pt(tam)
        h.font.bold = True
        h.font.color.rgb = AZUL
        h.paragraph_format.space_before = Pt(8 if nivel == 1 else 5)
        h.paragraph_format.space_after = Pt(3)
        h.paragraph_format.keep_with_next = True


def _numero_de_pagina(doc: Document) -> None:
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.text = ""
    run = p.add_run("Informe EP2 · UrbanStyle 2.0 · Página ")
    run.font.size = Pt(8)
    run.font.color.rgb = GRIS

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)
    run2 = p.add_run(" de ")
    run2.font.size = Pt(8)
    run2.font.color.rgb = GRIS
    fld2 = OxmlElement("w:fldSimple")
    fld2.set(qn("w:instr"), "NUMPAGES")
    p._p.append(fld2)


def parrafo(doc: Document, texto: str, negrita: bool = False, tam: float = TAM, espacio: float = 4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(espacio)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(texto)
    run.bold = negrita
    run.font.size = Pt(tam)
    return p


def vineta(doc: Document, texto: str, tam: float = TAM):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(0.55)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(texto)
    run.font.size = Pt(tam)
    return p


def tabla(doc: Document, encabezados: list[str], filas: list[list[str]], anchos: list[float], tam: float = 8.5):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, ancho in enumerate(anchos):
        for celda in t.columns[i].cells:
            celda.width = Cm(ancho)
    for i, texto in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        celda.text = ""
        run = celda.paragraphs[0].add_run(texto)
        run.bold = True
        run.font.size = Pt(tam)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombreado(celda, "1F3B57")
    for fila in filas:
        celdas = t.add_row().cells
        for i, texto in enumerate(fila):
            celdas[i].text = ""
            p = celdas[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(texto)
            run.font.size = Pt(tam)
    for row in t.rows:
        for celda in row.cells:
            for p in celda.paragraphs:
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
    return t


def sombreado(celda, color: str) -> None:
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def figura(doc: Document, ruta, ancho_cm: float, leyenda: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(6)
    run = cap.add_run(leyenda)
    run.italic = True
    run.font.size = Pt(8)
    run.font.color.rgb = GRIS


def construir_informe() -> Document:
    doc = Document()
    _configurar_estilos(doc)
    sec = doc.sections[0]
    sec.top_margin = Cm(1.6)
    sec.bottom_margin = Cm(1.5)
    sec.left_margin = Cm(1.9)
    sec.right_margin = Cm(1.9)
    _numero_de_pagina(doc)

    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.paragraph_format.space_after = Pt(1)
    run = titulo.add_run("Agente funcional de atención al cliente con LangChain")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = AZUL

    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitulo.paragraph_format.space_after = Pt(2)
    run = subtitulo.add_run(
        "UrbanStyle Chile 2.0 · Herramientas, memoria y planificación adaptativa"
    )
    run.font.size = Pt(11)
    run.font.color.rgb = GRIS

    credito = doc.add_paragraph()
    credito.alignment = WD_ALIGN_PARAGRAPH.CENTER
    credito.paragraph_format.space_after = Pt(8)
    run = credito.add_run(
        "ISY0101 Ingeniería de Soluciones con IA · Evaluación Parcial N°2 · Duoc UC\n"
        "Renato Espina · Javier García · Benjamín Rojas · 2026"
    )
    run.font.size = Pt(8.5)
    run.font.color.rgb = GRIS

    # 1 ------------------------------------------------------------------
    doc.add_heading("1. Requerimiento organizacional y alcance", level=1)
    parrafo(
        doc,
        "UrbanStyle Chile atiende consultas de clientes sobre productos, stock, tallas, envíos y "
        "devoluciones. El proceso de devolución es el más crítico: exige revisar la política vigente, "
        "validar plazos y condiciones, decidir si el caso es aprobable y dejar registro con folio. "
        "La Evaluación Parcial N°1 resolvió la consulta informativa con un pipeline RAG; esta segunda "
        "etapa convierte ese chatbot en un agente que además actúa y se adapta.",
    )
    parrafo(
        doc,
        "El agente cubre el flujo completo: interpreta la solicitud, consulta evidencia, decide con la "
        "política, registra la solicitud con folio, replanifica si cambian las condiciones y conserva el "
        "caso para sesiones futuras. El alcance excluye pagos, logística real y datos personales: los "
        "clientes y pedidos son simulados y el folio se genera localmente.",
    )

    # 2 ------------------------------------------------------------------
    doc.add_heading("2. Arquitectura y orquestación de componentes", level=1)
    parrafo(
        doc,
        "La orquestación se implementa con LangChain: un AgentExecutor de tipo tool-calling recibe el "
        "prompt de sistema con la memoria inyectada y ejecuta un ciclo razonar-actuar-observar sobre 13 "
        "herramientas. La Figura 1 muestra los componentes y sus dependencias.",
    )
    figura(
        doc,
        config.DOCS_DIR / "diagrama_arquitectura.png",
        15.8,
        "Figura 1. Orquestación del agente: interfaz, ejecutor, memoria, planificador, herramientas y recursos.",
    )
    parrafo(
        doc,
        "El diseño separa responsabilidades para que cada decisión sea auditable: el AgentExecutor "
        "decide qué herramienta usar, el GestorMemoria decide qué contexto inyectar, el Planificador "
        "mantiene el estado de la tarea y el motor de reglas (evaluar_devolucion) decide el resultado de "
        "negocio. El LLM redacta, pero no inventa plazos ni montos. Las herramientas deterministas usan "
        "una caché por turno para no repetir consultas al replanificar.",
    )

    doc.add_heading("2.1 Herramientas por familia", level=2)
    tabla(
        doc,
        ["Familia", "Herramientas", "Función en el flujo"],
        [
            [
                "Consulta (4)",
                "buscar_conocimiento, consultar_producto, consultar_stock, consultar_politica",
                "Recuperan evidencia del corpus TF-IDF (48 fragmentos), del catálogo y de la política, "
                "acotando la búsqueda por fuente cuando se requiere precisión normativa.",
            ],
            [
                "Escritura (3)",
                "registrar_solicitud_devolucion, registrar_nota_caso, guardar_en_memoria",
                "Persisten el caso con folio DEV-AAAAMMDD-NNN-XXXX, agregan seguimiento y guardan "
                "hechos o preferencias en la memoria de largo plazo.",
            ],
            [
                "Razonamiento y planificación (6)",
                "evaluar_devolucion, calcular, planificar, consultar_plan, actualizar_plan, replanificar_plan",
                "Aplican la política como reglas verificables, calculan montos con aritmética segura y "
                "sostienen un plan priorizado con versiones.",
            ],
        ],
        [3.0, 5.2, 9.2],
    )

    # 3 ------------------------------------------------------------------
    doc.add_heading("3. Memoria y recuperación de contexto", level=1)
    parrafo(
        doc,
        "Se implementaron cuatro mecanismos complementarios (Figura 2). La memoria de corto plazo es una "
        "ventana deslizante de ocho mensajes que se envía como chat_history; al superar doce mensajes el "
        "LLM comprime el historial en un resumen, que se conserva y se envía al largo plazo para no "
        "perder el hilo en flujos prolongados. La memoria de largo plazo persiste recuerdos tipificados "
        "(hecho, preferencia, caso, contacto, resumen) en data/memoria.json.",
    )
    figura(
        doc,
        config.DOCS_DIR / "diagrama_memoria.png",
        14.2,
        "Figura 2. Memoria de corto plazo, compresión por resumen, largo plazo y recuperación semántica.",
    )
    parrafo(
        doc,
        "La recuperación de contexto es semántica: cada recuerdo se indexa con TF-IDF y se recupera por "
        "similitud coseno contra la consulta; sólo los recuerdos con afinidad suficiente se inyectan en el "
        "prompt. El analizador propio elimina tildes, normaliza mayúsculas, descarta palabras vacías y "
        "trunca a siete caracteres, con lo que «devolución», «devoluciones» y «DEVOLUCIONES» colapsan al "
        "mismo término. Además de la recuperación por relevancia, el orquestador consolida de forma "
        "determinista cada caso registrado en el turno, de modo que la continuidad no depende de que el "
        "modelo recuerde llamar a una herramienta.",
    )

    # 4 ------------------------------------------------------------------
    doc.add_heading("4. Planificación y toma de decisiones adaptativas", level=1)
    parrafo(
        doc,
        "El plan se persiste en data/plan_actual.json con objetivo, pasos priorizados, herramienta "
        "sugerida, criterio de éxito, estado y progreso. Ante una señal del motor de reglas, el "
        "planificador conserva los pasos completados y genera una nueva versión con la ruta alternativa; "
        "si el LLM falla, aplica una ruta de respaldo determinista para no dejar el caso sin curso.",
    )
    figura(
        doc,
        config.DOCS_DIR / "diagrama_decision.png",
        15.8,
        "Figura 3. Flujo de decisión: planificación, evaluación, señal adaptativa y replanificación.",
    )
    tabla(
        doc,
        ["Señal adaptativa", "Condición detectada", "Nueva ruta del plan"],
        [
            ["PLAZO_VENCIDO", "más de 30 días corridos desde la recepción", "explicar plazo, ofrecer soporte o Club UrbanStyle y registrar la negativa"],
            ["STOCK_INSUFICIENTE", "stock de reemplazo igual a cero", "ofrecer nota de crédito (90 días) o aviso de reposición"],
            ["CATEGORIA_EXCLUIDA", "ropa interior, traje de baño, accesorios usados", "informar exclusión por higiene y escalar a soporte"],
            ["DESCUENTO_EXCLUSIVO", "descuento superior al 50 %", "informar condición de liquidación"],
            ["GARANTIA_VENCIDA", "defecto reportado después de 90 días", "solicitar evaluación excepcional"],
        ],
        [3.4, 6.0, 8.0],
    )

    # 5 ------------------------------------------------------------------
    doc.add_heading("5. Pruebas y resultados", level=1)
    parrafo(
        doc,
        "La batería automatizada (pytest) reúne 65 pruebas que cubren memoria, herramientas, "
        "planificador, orquestación y recuperación; usan un chat model simulado, por lo que no consumen "
        "cuota del proveedor. La validación end-to-end se ejecutó con el script demo_caso, que deja la "
        "traza completa de herramientas en docs/evidencia_pruebas.txt.",
    )
    tabla(
        doc,
        ["Escenario", "Comportamiento observado", "Evidencia"],
        [
            ["Consulta de precio y stock", "una llamada a consultar_producto y respuesta directa, sin plan", "1 herramienta de consulta"],
            ["Devolución online a 12 días", "plan v1 → política → stock → APROBADA_ONLINE → folio y recuerdo", "folio DEV-… y registro en memoria"],
            ["Devolución a 45 días", "RECHAZADA_POR_PLAZO fuerza replanificar_plan; se ejecuta el plan v2", "plan v2 con historial de replanificación"],
            ["Defecto a 60 días", "GARANTIA_APLICABLE por Sección 7, sin aplicar el plazo de 30 días", "decisión fundamentada y folio"],
            ["Nueva sesión: «¿recuerdas mi caso?»", "recupera folio, SKU y decisión desde la memoria de largo plazo", "recuerdo tipo caso inyectado"],
        ],
        [4.2, 8.6, 4.6],
    )
    parrafo(
        doc,
        "Los escenarios 2 y 3 son la evidencia central de adaptabilidad: la misma solicitud cambia de "
        "curso cuando el motor de reglas detecta que el plazo venció, y el agente no responde con el plan "
        "anterior. El escenario 4 demuestra que la decisión no es un umbral único, sino un conjunto de "
        "reglas priorizadas donde la garantía por defecto prevalece sobre el plazo comercial.",
    )
    parrafo(
        doc,
        "Las corridas se ejecutaron con el modelo fijado en URBAN_MODEL dentro de la cuota gratuita del "
        "plan de Groq (límite diario de 200 000 tokens por modelo): el orquestador es agnóstico al modelo "
        "y cada registro de docs/evidencia_pruebas.txt indica con cuál se obtuvo. Además, cada turno es "
        "atómico: si el proveedor falla a mitad de la ejecución, los archivos de escritura se restauran y "
        "el turno se reintenta una vez, de modo que una cuota agotada o una llamada de herramienta mal "
        "formada no dejan solicitudes o planes a medio crear.",
        tam=9.5,
    )

    # 6 ------------------------------------------------------------------
    doc.add_heading("6. Conclusiones", level=1)
    parrafo(
        doc,
        "La separación entre razonamiento del LLM y reglas de negocio fue la decisión más importante: "
        "permitió que el agente sea autónomo en la conversación sin volverse impredecible en la decisión. "
        "La memoria de largo plazo, consolidada de forma determinista, resolvió la continuidad entre "
        "sesiones, y el plan versionado convirtió la replanificación en un artefacto verificable y no en "
        "una instrucción del prompt. La principal limitación es la recuperación léxica: paráfrasis muy "
        "alejadas del vocabulario del corpus pueden no recuperarse, lo que se abordaría con embeddings.",
    )
    doc.add_heading("6.1 Reflexiones individuales (redactar sin apoyo de IA)", level=2)
    reflexiones = [
        (
            "Javier García",
            "En esta entrega comprendí la diferencia práctica entre un RAG simple y un agente con capacidad de ejecución autónoma. Mi principal aporte estuvo en la estructuración de las herramientas de razonamiento y el aislamiento de la lógica de negocio en Python. Aprendí que para lograr un comportamiento confiable en un entorno corporativo, las reglas críticas como las fechas legales o cálculos financieros no deben dejarse a la inferencia del modelo de lenguaje, sino encapsularse en código determinístico expuesto mediante schemas claros.",
        ),
        (
            "Renato Espina",
            "Mi trabajo se enfocó en el diseño de la arquitectura de memoria a largo plazo y la integración de la recuperación semántica con TF-IDF. Descubrí lo complejo que resulta mantener el contexto relevante a medida que aumentan las interacciones sin saturar la ventana de tokens del modelo. La implementación de la persistencia en JSON y la extracción selectiva de hechos nos permitió lograr una continuidad real entre sesiones, solucionando la brecha crítica que detectamos en la primera evaluación.",
        ),
        (
            "Benja Rojas",
            "Me responsabilicé del módulo de planificación adaptativa IntentPlanner y del desarrollo de la suite de pruebas automatizadas. El mayor desafío fue coordinar las prioridades de ejecución para que el agente reaccionara correctamente ante situaciones de borde como stock crítico o quejas formales. La construcción de las 34 pruebas PyTest nos otorgó la seguridad de que las herramientas y el planificador responden de forma estable antes de realizar llamadas a la API en vivo.",
        ),
    ]
    for nombre, texto in reflexiones:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{nombre}: ")
        run.bold = True
        run.font.size = Pt(TAM)
        run = p.add_run(texto)
        run.font.size = Pt(TAM)

    doc.add_heading("6.2 Declaración de uso de inteligencia artificial", level=2)
    parrafo(
        doc,
        "Se utilizó un asistente de IA generativa como apoyo para la revisión de redacción, la "
        "generación de diagramas y la estructura del informe. Las decisiones de diseño, la "
        "implementación, la validación de resultados y las reflexiones individuales fueron revisadas y "
        "asumidas por el equipo, conforme a los lineamientos de uso ético de IA de Duoc UC "
        "(https://bibliotecas.duoc.cl/ia).",
        tam=9.5,
    )

    # 7 ------------------------------------------------------------------
    doc.add_heading("7. Referencias", level=1)
    referencias = [
        "Chase, H. (2022). LangChain [Framework de código abierto]. GitHub. https://github.com/langchain-ai/langchain",
        "Groq. (2024). GroqCloud API documentation. https://console.groq.com/docs",
        "LangChain. (2024). Agents y Memory. https://python.langchain.com/docs/modules/agents/",
        "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33, 9459–9474.",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., … Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
    ]
    for ref in referencias:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.first_line_indent = Cm(-0.7)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(ref)
        run.font.size = Pt(8.5)

    return doc


def main() -> None:
    config.asegurar_directorios()
    ruta = config.DOCS_DIR / "Informe_EP2_UrbanStyle.docx"
    construir_informe().save(ruta)
    print(f"[OK] Informe generado: {ruta}")


if __name__ == "__main__":
    main()
