import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from groq import Groq
from dotenv import load_dotenv

from src.load_documents import load_all_documents
from src.prompts import SYSTEM_PROMPT, CONTEXT_WRAPPER, FALLBACK_RESPONSE

load_dotenv()

# Modelo de Groq. Se usa gpt-oss-120b porque el plan gratuito de qwen tiene
# un límite muy bajo de tokens de salida por minuto (OTPM=1000), lo que hace
# fallar respuestas largas con error 429.
MODEL = "openai/gpt-oss-120b"


class LocalRetriever:
    """Recuperador local basado en TF-IDF. No requiere LangChain ni servicios de embeddings."""

    def __init__(self, k: int = 4):
        self.k = k
        self.docs = []
        self.texts = []
        self.vectorizer = None
        self.vectors = None
        self.is_built = False

    def build(self):
        self.docs = load_all_documents()
        self.texts = [d.page_content for d in self.docs]
        self.vectorizer = TfidfVectorizer(stop_words=None)
        self.vectors = self.vectorizer.fit_transform(self.texts)
        self.is_built = True
        print(f"[INFO] Documentos indexados: {len(self.docs)} chunks (retriever TF-IDF local)")

    def get_relevant_documents(self, query: str):
        if not self.is_built:
            self.build()
        q_vec = self.vectorizer.transform([query])
        scores = np.asarray((q_vec @ self.vectors.T).todense()).flatten()
        top_idx = scores.argsort()[-self.k:][::-1]
        results = []
        for idx in top_idx:
            if scores[idx] > 0:
                results.append(self.docs[int(idx)])
        return results if results else self.docs[: self.k]


def get_client() -> Groq:
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def create_rag_chain(temperature: float = 0.3):
    retriever = LocalRetriever(k=4)
    retriever.build()
    return {"retriever": retriever, "client": get_client(), "model": MODEL}


def query(chain: dict, question: str) -> dict:
    retriever = chain["retriever"]
    client = chain["client"]
    model = chain["model"]

    relevant = retriever.get_relevant_documents(question)
    context = "\n\n---\n\n".join(d.page_content for d in relevant)

    prompt = SYSTEM_PROMPT + "\n\n" + CONTEXT_WRAPPER.format(context=context, question=question)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    answer = response.choices[0].message.content

    sources = list(set(d.metadata.get("source", "desconocido") for d in relevant))
    return {"answer": answer, "sources": sources}
