"""Ingest all authorized NIEL PDFs into FAISS store."""

from datetime import datetime, timezone
import logging
from pathlib import Path
import sys

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import get_settings
from backend.app.ingestion.chunker import process_document_to_chunks
from backend.app.ingestion.extractor import extract_pages_from_pdf, extract_text_from_plain, ScannedDocumentError
from backend.app.ingestion.hasher import compute_sha256_bytes
from backend.app.retrieval.faiss_store import get_faiss_store
from backend.app.schemas.documents import DocumentSummary
from backend.app.services.openai_service import get_openai_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("niel_indexer")


def main():
    settings = get_settings()
    pdf_dir = Path("PDFs")
    if not pdf_dir.exists():
        logger.error("PDFs folder not found.")
        sys.exit(1)

    store = get_faiss_store()
    store.clear()
    openai_service = get_openai_service()

    pdf_files = sorted(list(pdf_dir.glob("*.pdf")))
    logger.info("Found %d PDF files in %s", len(pdf_files), pdf_dir)

    total_added = 0
    total_docs = 0

    for pdf_path in pdf_files:
        content = pdf_path.read_bytes()
        doc_id = compute_sha256_bytes(content)

        if store.is_document_indexed(doc_id):
            logger.info("Already indexed: %s (hash: %s...)", pdf_path.name, doc_id[:8])
            continue

        try:
            pages = extract_pages_from_pdf(content)
        except ScannedDocumentError as exc:
            logger.warning("Skipping scanned PDF %s: %s", pdf_path.name, exc)
            continue
        except Exception as exc:
            logger.error("Error extracting %s: %s", pdf_path.name, exc)
            continue

        chunks = process_document_to_chunks(pages, doc_id, pdf_path.name)
        if not chunks:
            logger.warning("No text chunks generated for %s", pdf_path.name)
            continue

        texts = [chunk.text for chunk in chunks]
        embeddings = openai_service.get_embeddings_batch(texts)

        summary = DocumentSummary(
            doc_id=doc_id,
            filename=pdf_path.name,
            page_count=len(pages),
            chunk_count=len(chunks),
            file_size_bytes=len(content),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        store.add_document_chunks(summary, chunks, embeddings)
        total_added += len(chunks)
        total_docs += 1
        logger.info("[SUCCESS] Indexed %s: %d pages, %d chunks", pdf_path.name, len(pages), len(chunks))

    # Also ingest structured text versions from textpdfs
    text_dir = Path("textpdfs")
    if text_dir.exists():
        text_files = sorted(list(text_dir.glob("*.txt")))
        logger.info("Found %d text files in %s", len(text_files), text_dir)
        for txt_path in text_files:
            content = txt_path.read_bytes()
            doc_id = compute_sha256_bytes(content)

            # Attribute Pumps directly to the official brochure PDF
            if "Pumps" in txt_path.name:
                source_name = "Pumps - NIEL Brochure.pdf"
            else:
                source_name = txt_path.name

            pages = extract_text_from_plain(content, source_name)
            chunks = process_document_to_chunks(pages, doc_id, source_name, chunk_size=600, chunk_overlap=120)
            if not chunks:
                continue

            texts = [chunk.text for chunk in chunks]
            embeddings = openai_service.get_embeddings_batch(texts)

            summary = DocumentSummary(
                doc_id=doc_id,
                filename=source_name,
                page_count=len(pages),
                chunk_count=len(chunks),
                file_size_bytes=len(content),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            store.add_document_chunks(summary, chunks, embeddings)
            total_added += len(chunks)
            total_docs += 1
            logger.info("[SUCCESS] Indexed Text Spec %s: %d chunks", source_name, len(chunks))

    logger.info("FINISHED. Store now contains %d chunks across %d documents.", store.index.ntotal, len(store.documents))


if __name__ == "__main__":
    main()
