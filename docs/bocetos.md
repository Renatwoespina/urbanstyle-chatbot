# Bocetos de diseño

Anotaciones iniciales del equipo (pizarra y papel) que antecedieron a la
implementación. No son dibujos definitivos: muestran el orden en que se
decidieron las piezas y los puntos donde cambiamos de idea antes de escribir
código. Se complementan con los diagramas finales de `docs/diagrama_*.png`
y con el diagrama Mermaid del `README.md`.

## 1. Flujo principal (atención + devolución)

```
        cliente escribe
              |
              v
   +----------------------+      sin caso activo
   |  ¿es caso de         |--------------------->  consulta directa
   |  devolución?         |                        (producto/stock)
   +----------------------+
              | sí
              v
   +----------------------+        plazo vencido /
   | planificar(contexto, | <----- condición nueva
   | objetivo)  -> plan v1|                          |
   +----------------------+                          v
              |                          +---------------------+
              v                          | replanificar_plan   |
   consultar_politica /                  |  -> plan v2 (+1)    |
   consultar_stock /                     +---------------------+
   consultar_producto                             |
              |                                   v
              v                        evaluar_devolucion (reglas)
   evaluar_devolucion (motor de reglas)          |
       APROBADA / RECHAZADA / GARANTIA           v
              |                        registrar_solicitud_devolucion
              v                                   |
   registrar_solicitud_devolucion  <--------------+
              |
              v
        folio DEV-AAAAAMMDD-nnn-XXXX  ----->  memoria de largo plazo
              |                                     |
              v                                     v
        respuesta al cliente               (recuperación semántica en
                                            la sesión siguiente)
```

Decisión clave: la **decisión de negocio nunca la toma el LLM**. El LLM arma la
llamada y redacta la respuesta; `evaluar_devolucion` aplica la política y
devuelve un veredicto reproducible.

## 2. Memoria (borrador)

```
sesión (corto plazo, ventana de 8 mensajes)
   |  si el turno supera el resumen -> summarization en memoria "resumen"
   v
turno completo: entrada + respuesta + traza de herramientas
   |
   v  consolidar_traza()  <- regex determinista (no LLM) buscando folios,
   |                         hechos, preferencias y casos
   v
data/memoria.json   tipo: hecho | preferencia | caso | contacto | resumen
   |
   v  búsqueda semántica TF-IDF sobre los fragmentos de los recuerdos
   +--> bloque de texto "[MEMORIA DEL AGENTE ...]" inyectado en el prompt
        de la sesión siguiente
```

Duda que resolvimos en el camino: si dejábamos que el LLM redactara el
recuerdo, inventaba folios. Se optó por extraer el recuerdo de la traza real.

## 3. Planificador y replanificación

```
planificar -> plan v1 { objetivo, pasos[] priorizados, herramienta sugerida }
                    |
        actualizar_plan(paso, estado, nota)   (progreso %)
                    |
        condición cambia (ej. RECHAZADA_POR_PLAZO)
                    |
        replanificar_plan(nuevo_objeto, motivo)  -->  plan v2
        versiones anteriores se conservan en "historial"  -->  auditable

persistencia: data/plan_actual.json  (sobrevive a reinicios de sesión)
```

## 4. Detalles que se ajustaron durante la implementación

- Fragmentación del corpus: se probaron 500/200 y quedó `chunk_size=300`,
  `overlap=60` con corte en saltos de línea para no cortar oraciones a la mitad.
- Umbral de similitud: `SCORE_MINIMO=0.05` para que preguntas sin relación
  (p. ej. "xyzzy plugh") devuelvan vacío en lugar de un fragmento cualquiera.
- Turno atómico: si el proveedor falla a mitad del turno, los JSON de escritura
  se restauran y el turno se reintenta una vez (evita folios a medias).
- Recuperación semántica: prefijo de 7 caracteres + stopwords + sinónimos, ya
  que el TF-IDF local es léxico y "costarán" no matchea con "precio".
