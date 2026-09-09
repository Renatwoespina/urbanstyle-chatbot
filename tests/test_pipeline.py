import pytest
from src.load_documents import load_all_documents, load_catalog, load_faq


def test_load_catalog():
    docs = load_catalog()
    assert len(docs) == 15
    assert "URB-001" in docs[0].page_content
    assert "$12990" in docs[0].page_content


def test_load_faq():
    docs = load_faq()
    assert len(docs) >= 1
    assert "horarios" in docs[0].page_content.lower()


def test_load_all_documents():
    docs = load_all_documents()
    assert len(docs) > 15


def test_document_chunks():
    from src.load_documents import split_documents
    docs = load_faq()
    chunks = split_documents(docs, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > len(docs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
