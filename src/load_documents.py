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
    """Divide documentos largos en fragmentos respetando límites de párrafo u oración.

    Se busca el último salto de línea (o punto) dentro de la ventana para no
    cortar palabras ni secciones por la mitad, lo que mejora la legibilidad de
    la evidencia que recibe el LLM.
    """
    chunks = []
    for doc in docs:
        content = doc.page_content
        if len(content) <= chunk_size:
            chunks.append(doc)
            continue
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            if end < len(content):
                ventana = content[start : end]
                corte = max(ventana.rfind("\n"), ventana.rfind(". "))
                if corte > chunk_size // 2:
                    end = start + corte + 1
            fragmento = content[start:end].strip()
            if fragmento:
                chunks.append(Document(fragmento, doc.metadata))
            if end >= len(content):
                break
            start = max(end - chunk_overlap, start + 1)
            # Evita que el siguiente fragmento comience en medio de una palabra.
            if start > 0 and content[start - 1] not in " \n":
                espacio = content.find(" ", start)
                if 0 <= espacio - start <= 40:
                    start = espacio + 1
    return chunks


def load_all_documents(chunk_size: int = 300, chunk_overlap: int = 60) -> list[Document]:
    """Corpus unificado.

    Los documentos largos se fragmentan en trozos de 300 caracteres: con trozos
    menores la similitud TF-IDF no se diluye y el retriever prioriza el pasaje
    exacto (mejora medida sobre consultas de tallas y devoluciones).
    """
    all_docs = []
    all_docs.extend(load_catalog())
    all_docs.extend(split_documents(load_faq(), chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    all_docs.extend(split_documents(load_policies(), chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    all_docs.extend(split_documents(load_size_guide(), chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return all_docs
