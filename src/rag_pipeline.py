"""Pipeline de recuperación (RAG) y acceso al LLM.

Se conserva el retriever TF-IDF local de la Evaluación Parcial 1 y se extiende
para permitir **recuperación acotada por fuente** (p. ej. solo política de
devoluciones), lo que permite al agente aislar la evidencia que usa su razonamiento.
"""

from __future__ import annotations

import os

import numpy as np
from dotenv import load_dotenv
from groq import Groq
from sklearn.feature_extraction.text import TfidfVectorizer

from src import config
from src.load_documents import load_all_documents, load_policies
from src.prompts import CONTEXT_WRAPPER, FALLBACK_RESPONSE, SYSTEM_PROMPT
from src.texto import analizador

load_dotenv(config.BASE_DIR / ".env")

MODEL = config.MODEL


class LocalRetriever:
    """Recuperador local basado en TF-IDF. Sin servicios externos de embeddings."""

    #: Similitud coseno mínima para aceptar un fragmento como evidencia.
    SCORE_MINIMO = 0.05

    def __init__(self, k: int = config.TOP_K_RAG, score_minimo: float | None = None):
        self.k = k
        self.score_minimo = self.SCORE_MINIMO if score_minimo is None else score_minimo
        self.docs = []
        self.texts = []
        self.vectorizer = None
        self.vectors = None
        self.is_built = False

    def build(self, docs=None):
        self.docs = docs if docs is not None else load_all_documents()
        self.texts = [d.page_content for d in self.docs]
        self.vectorizer = TfidfVectorizer(analyzer=analizador, stop_words=None)
        self.vectors = self.vectorizer.fit_transform(self.texts)
        self.is_built = True
        print(f"[INFO] Documentos indexados: {len(self.docs)} chunks (retriever TF-IDF local)")

    def get_relevant_documents(self, query: str, fuentes: list[str] | None = None, k: int | None = None):
        if not self.is_built:
            self.build()
        candidatos = list(range(len(self.docs)))
        if fuentes:
            candidatos = [
                i for i in candidatos if self.docs[i].metadata.get("source") in fuentes
            ]
        if not candidatos:
            return []
        q_vec = self.vectorizer.transform([query])
        scores = np.asarray((q_vec @ self.vectors.T).todense()).flatten()
        ordenados = sorted(candidatos, key=lambda i: scores[i], reverse=True)
        limite = k or self.k
        return [
            self.docs[i] for i in ordenados[:limite] if scores[i] >= self.score_minimo
        ]


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY no está definida en .env")
    return Groq(api_key=api_key)


def crear_retriever(k: int = config.TOP_K_RAG) -> LocalRetriever:
    retriever = LocalRetriever(k=k)
    retriever.build()
    return retriever


def recuperar_fragments(
    retriever: LocalRetriever, query: str, fuentes: list[str] | None = None, k: int | None = None
) -> tuple[str, list[str]]:
    """Devuelve (contexto armado, lista de fuentes) para una consulta."""
    docs = retriever.get_relevant_documents(query, fuentes=fuentes, k=k)
    contexto = "\n\n---\n\n".join(d.page_content for d in docs)
    fuentes_obtenidas = sorted({d.metadata.get("source", "desconocido") for d in docs})
    return contexto, fuentes_obtenidas


def politica_completa() -> str:
    return "\n".join(d.page_content for d in load_policies())


def invocar_llm(system: str, user: str, temperatura: float = config.TEMPERATURE, model: str | None = None) -> str:
    """Invocación única al LLM usada por prompts de planificación y resúmenes."""
    client = get_client()
    response = client.chat.completions.create(
        model=model or config.MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperatura,
    )
    return response.choices[0].message.content or ""


def create_rag_chain(temperature: float = 0.3):
    """Interfaz compatible con la versión 1.x del proyecto."""
    retriever = crear_retriever()
    return {"retriever": retriever, "client": get_client(), "model": config.MODEL, "temperature": temperature}


def query(chain: dict, question: str) -> dict:
    retriever = chain["retriever"]
    client = chain["client"]
    model = config.MODEL

    relevant = retriever.get_relevant_documents(question)
    context = "\n\n---\n\n".join(d.page_content for d in relevant)

    prompt = SYSTEM_PROMPT + "\n\n" + CONTEXT_WRAPPER.format(context=context, question=question)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=chain.get("temperature", 0.3),
    )
    answer = response.choices[0].message.content

    sources = list(set(d.metadata.get("source", "desconocido") for d in relevant))
    return {"answer": answer, "sources": sources}


__all__ = [
    "LocalRetriever",
    "MODEL",
    "FALLBACK_RESPONSE",
    "crear_retriever",
    "recuperar_fragments",
    "politica_completa",
    "invocar_llm",
    "create_rag_chain",
    "query",
]
