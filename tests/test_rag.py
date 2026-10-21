"""Pruebas del recuperador semántico (RAG TF-IDF) y del analizador de texto."""

from __future__ import annotations

from src.load_documents import load_all_documents, split_documents
from src.rag_pipeline import recuperar_fragments
from src.texto import analizador, normalizar


def test_normalizar_quita_tildes_y_mayusculas():
    assert normalizar("Guía de TALLAS") == "guia de tallas"


def test_analizador_descarta_vacias():
    assert "de" not in analizador("guia de tallas")


def test_recuperar_devuelve_contexto_y_fuentes(retriever):
    contexto, fuentes = recuperar_fragments(retriever, "¿cuál es el plazo de devolución?")
    assert contexto
    assert fuentes
    assert "30" in contexto


def test_recuperar_filtra_por_fuente(retriever):
    _, fuentes = recuperar_fragments(
        retriever, "devolución", fuentes=["politica_devoluciones"], k=3
    )
    assert set(fuentes) == {"politica_devoluciones"}


def test_recuperar_guia_de_tallas(retriever):
    contexto, fuentes = recuperar_fragments(retriever, "guia de tallas", k=5)
    assert "guia_tallas" in fuentes


def test_recuperar_consulta_sin_coincidencias(retriever):
    contexto, _ = recuperar_fragments(retriever, "xyzzy plugh")
    assert contexto == ""


def test_chunks_respetan_tamano():
    docs = load_all_documents()
    assert len(docs) >= 40
    assert all(len(d.page_content) <= 400 for d in docs)


def test_split_respeta_limites_de_parrafo():
    from langchain_core.documents import Document

    texto = "Primera idea completa. " * 30
    chunks = split_documents([Document(texto)], chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 100 for c in chunks)
