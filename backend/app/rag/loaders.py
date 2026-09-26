"""
Document loaders for multiple file formats.
Each loader returns a list of LangChain Document objects.
"""
from pathlib import Path
from typing import Any

import structlog
from langchain_core.documents import Document

log = structlog.get_logger(__name__)


def load_document(file_path: str) -> list[Document]:
    """
    Dispatch to the appropriate loader based on file extension.
    Returns a list of LangChain Document objects (one per page/section).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    loaders = {
        ".pdf": _load_pdf,
        ".docx": _load_docx,
        ".doc": _load_docx,
        ".txt": _load_txt,
        ".md": _load_txt,
        ".csv": _load_csv,
        ".pptx": _load_pptx,
        ".xlsx": _load_xlsx,
    }

    loader_fn = loaders.get(suffix, _load_txt)
    docs = loader_fn(str(path))

    if not docs:
        log.warning("Loader returned empty results", path=file_path, suffix=suffix)

    return docs


def _load_pdf(file_path: str) -> list[Document]:
    """Load PDF using PyPDF with page-level metadata."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        # Normalize metadata keys
        for i, doc in enumerate(docs):
            doc.metadata["page"] = doc.metadata.get("page", i)
        return docs
    except Exception as e:
        log.error("PDF loading failed", path=file_path, error=str(e))
        # Fallback to unstructured if PyPDF fails
        return _load_unstructured(file_path)


def _load_docx(file_path: str) -> list[Document]:
    """Load DOCX using python-docx."""
    try:
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
        return loader.load()
    except Exception as e:
        log.error("DOCX loading failed", path=file_path, error=str(e))
        return _load_unstructured(file_path)


def _load_txt(file_path: str) -> list[Document]:
    """Load plain text files."""
    try:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)
        return loader.load()
    except Exception as e:
        log.error("TXT loading failed", path=file_path, error=str(e))
        return []


def _load_csv(file_path: str) -> list[Document]:
    """Load CSV files row-by-row as text."""
    try:
        from langchain_community.document_loaders.csv_loader import CSVLoader
        loader = CSVLoader(file_path)
        return loader.load()
    except Exception as e:
        log.error("CSV loading failed", path=file_path, error=str(e))
        return []


def _load_pptx(file_path: str) -> list[Document]:
    """Load PowerPoint presentations."""
    try:
        from langchain_community.document_loaders import UnstructuredPowerPointLoader
        loader = UnstructuredPowerPointLoader(file_path)
        return loader.load()
    except Exception as e:
        log.error("PPTX loading failed", path=file_path, error=str(e))
        return []


def _load_xlsx(file_path: str) -> list[Document]:
    """Load Excel spreadsheets."""
    try:
        from langchain_community.document_loaders import UnstructuredExcelLoader
        loader = UnstructuredExcelLoader(file_path, mode="elements")
        return loader.load()
    except Exception as e:
        log.error("XLSX loading failed", path=file_path, error=str(e))
        return []


def _load_unstructured(file_path: str) -> list[Document]:
    """Fallback: use unstructured library for any file type."""
    try:
        from langchain_community.document_loaders import UnstructuredFileLoader
        loader = UnstructuredFileLoader(file_path)
        return loader.load()
    except Exception as e:
        log.error("Unstructured loader failed", path=file_path, error=str(e))
        return []
