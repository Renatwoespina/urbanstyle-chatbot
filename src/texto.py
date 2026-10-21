"""Normalización de texto en español para el recuperador TF-IDF.

Sin stemming externo, se aplica una normalización ligera:

1. se eliminan tildes y diacríticos (NFKD),
2. se pasa a minúsculas,
3. se trunca cada palabra a sus primeros `PREFIJO` caracteres, lo que aproxima
   un stemming y evita que "devolución" y "devoluciones" queden como términos
   distintos en la matriz TF-IDF.

Esto es clave para la recuperación semántica de la memoria y para que el agente
encuentre el pasaje correcto de la política con consultas naturales.
"""

from __future__ import annotations

import re
import unicodedata

PREFIJO = 7
_PATRON = re.compile(r"[a-z0-9]+")

#: Palabras funcionales que no aportan señal a la similitud TF-IDF.
STOPWORDS = frozenset(
    "de la el los las un una unos unas y o u que en con por para del al se su sus "
    "mi tu es son como mas pero si no lo le les este esta estos estas hay muy "
    "me te nos ser esta estan".split()
)


def sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    return sin_acentos(texto or "").lower()


def tokenizar(texto: str) -> list[str]:
    return [
        t[:PREFIJO]
        for t in _PATRON.findall(normalizar(texto))
        if len(t) > 1 and t not in STOPWORDS
    ]


def analizador(texto: str) -> list[str]:
    """Analyzer compatible con scikit-learn `TfidfVectorizer(analyzer=...)`."""
    return tokenizar(texto)
