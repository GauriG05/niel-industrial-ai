"""Unit and integration tests for document ingestion and vector storage."""

import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.ingestion.extractor import (
    extract_pages_from_pdf,
    ExtractionError,
    ScannedDocumentError,
)
from backend.app.ingestion.chunker import chunk_page_text, process_document_to_chunks
from backend.app.retrieval.faiss_store import get_faiss_store
from backend.app.services.openai_service import get_openai_service

client = TestClient(app)
settings = get_settings()

SAMPLE_PDF_PATH = "data/docs/NIEL_Industrial_Motors_Catalogue_2026.pdf"


@pytest.fixture(autouse=True)
def clean_test_index():
    """Ensure a clean FAISS index for ingestion tests."""
    store = get_faiss_store()
    store.clear()
    yield
    store.clear()


def test_pdf_extraction_success():
    """Verify text is extracted page by page from valid PDF."""
    with open(SAMPLE_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages_from_pdf(pdf_bytes)
    assert len(pages) == 2
    assert pages[0][0] == 1  # 1-indexed
    assert "0.75 kW to 315 kW" in pages[0][1]
    assert pages[1][0] == 2
    assert "Mounting Types: Foot mounted B3" in pages[1][1]


def test_invalid_pdf_rejected():
    """Verify files without %PDF- magic bytes are rejected."""
    invalid_bytes = b"This is plain text pretending to be a pdf"
    with pytest.raises(ExtractionError):
        extract_pages_from_pdf(invalid_bytes)


def test_scanned_pdf_detection():
    """Verify scanned PDFs with 0 extractable text raise ScannedDocumentError."""
    # Construct a valid PDF structure with an empty page (0 text characters)
    empty_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n198\n%%EOF"
    )
    with pytest.raises(ScannedDocumentError):
        extract_pages_from_pdf(empty_pdf)


def test_chunking_preserves_metadata():
    """Verify chunking maintains exact page and file metadata."""
    text = "Sentence one about motor efficiency. Sentence two about 415V rating. Sentence three about IP55 enclosure."
    chunks = chunk_page_text(
        text=text,
        page_number=1,
        doc_id="test_doc_hash_12345",
        source_filename="catalogue.pdf",
        chunk_size=50,
        chunk_overlap=15,
    )
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "test_doc_hash_12345"
        assert chunk.page_number == 1
        assert chunk.source_filename == "catalogue.pdf"
        assert len(chunk.text) > 0

