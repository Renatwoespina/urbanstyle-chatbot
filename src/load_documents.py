import csv
import os


class Document:
    """Contenedor simple de un documento de texto con metadata."""

    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Document({len(self.page_content)} chars, source={self.metadata.get('source')})"


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_faq() -> list[Document]:
    path = os.path.join(DATA_DIR, "faq.txt")
    return [Document(_read_text_file(path), {"source": "faq"})]


def load_policies() -> list[Document]:
    path = os.path.join(DATA_DIR, "politica_devoluciones.txt")
    return [Document(_read_text_file(path), {"source": "politica_devoluciones"})]


def load_size_guide() -> list[Document]:
    path = os.path.join(DATA_DIR, "guia_tallas.txt")
    return [Document(_read_text_file(path), {"source": "guia_tallas"})]


def load_catalog() -> list[Document]:
    path = os.path.join(DATA_DIR, "catalogo_productos.csv")
    docs = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"Producto: {row['nombre']}\n"
                f"SKU: {row['sku']}\n"
                f"Categoría: {row['categoria']}\n"
                f"Precio: ${row['precio_stock']}\n"
                f"Stock: {row['stock']} unidades\n"
                f"Tallas disponibles: {row['talla']}\n"
                f"Colores: {row['color']}\n"
                f"Descripción: {row['descripcion']}\n"
            )
            docs.append(Document(text, {"source": "catalogo", "sku": row["sku"]}))
    return docs


def split_documents(docs: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    """Divide documentos largos en fragmentos. Simple y sin dependencias."""
    chunks = []
    for doc in docs:
        content = doc.page_content
        if len(content) <= chunk_size:
            chunks.append(doc)
            continue
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunks.append(Document(content[start:end], doc.metadata))
            if end >= len(content):
                break
            start = end - chunk_overlap
    return chunks


def load_all_documents() -> list[Document]:
    all_docs = []
    all_docs.extend(load_catalog())
    all_docs.extend(split_documents(load_faq()))
    all_docs.extend(split_documents(load_policies()))
    all_docs.extend(split_documents(load_size_guide()))
    return all_docs
