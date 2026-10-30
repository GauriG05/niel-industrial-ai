"""Document management endpoints: upload, listing, and deletion."""

from datetime import datetime, timezone
import os
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.config import Settings, get_settings
from backend.app.schemas.documents import (
    DocumentListResponse,
    DocumentSummary,
    IngestionResponse,
)
from backend.app.ingestion.hasher import compute_sha256_bytes
from backend.app.ingestion.extractor import (
    extract_pages_from_pdf,
    extract_text_from_plain,
    ExtractionError,
    ScannedDocumentError,
)
from backend.app.ingestion.chunker import process_document_to_chunks
from backend.app.services.openai_service import get_openai_service
from backend.app.retrieval.faiss_store import get_faiss_store
from backend.app.security.auth import verify_admin_key

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=IngestionResponse)
async def upload_document(
    file: UploadFile = File(...),
    admin_auth: str = Depends(verify_admin_key),
    settings: Settings = Depends(get_settings),
):
    """
    Secure document ingestion endpoint.
    Restricted to authorized administrators via X-Admin-Key.
    """
    # 1. Enforce filename sanity (prevent directory traversal)
    clean_filename = Path(file.filename or "unknown.pdf").name
    if not clean_filename or clean_filename.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename supplied.",
        )

    # 2. Read content & enforce size limits
    content = await file.read()
    file_size_bytes = len(content)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    if file_size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # 3. Compute deterministic hash for deduplication
    doc_id = compute_sha256_bytes(content)
    faiss_store = get_faiss_store()

    if faiss_store.is_document_indexed(doc_id):
        return IngestionResponse(
            status="duplicate_skipped",
            doc_id=doc_id,
            filename=clean_filename,
            chunks_indexed=0,
            pages_processed=0,
            message="Document is already indexed with identical SHA-256 hash. Skipping re-indexing.",
        )

    # 4. Extract pages based on content inspection
    is_pdf = clean_filename.lower().endswith(".pdf")
    is_txt = clean_filename.lower().endswith((".txt", ".md"))

    try:
        if is_pdf:
            pages = extract_pages_from_pdf(content)
        elif is_txt:
            pages = extract_text_from_plain(content, clean_filename)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported document format. Only PDF, TXT, and MD files are authorized.",
            )
    except ScannedDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scanned document detected: {str(exc)}",
        )
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extraction failure: {str(exc)}",
        )

    # 5. Process into overlapping chunks with metadata
    chunks = process_document_to_chunks(
        pages=pages,
        doc_id=doc_id,
        source_filename=clean_filename,
        chunk_size=700,
        chunk_overlap=150,
    )

    if len(chunks) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contained no extractable textual content after processing.",
        )

    # 6. Generate embeddings
    openai_service = get_openai_service()
    chunk_texts = [c.text for c in chunks]
    embeddings = openai_service.get_embeddings_batch(chunk_texts)

    # 7. Create summary and index into FAISS
    summary = DocumentSummary(
        doc_id=doc_id,
        filename=clean_filename,
        page_count=len(pages),
        chunk_count=len(chunks),
        created_at=datetime.now(timezone.utc).isoformat(),
        file_size_bytes=file_size_bytes,
    )
    faiss_store.add_document_chunks(summary, chunks, embeddings)

    # 8. Safely persist original document to docs storage
    save_path = settings.DOCS_DIR / f"{doc_id}_{clean_filename}"
    with open(save_path, "wb") as f:
        f.write(content)

    return IngestionResponse(
        status="indexed",
        doc_id=doc_id,
        filename=clean_filename,
        chunks_indexed=len(chunks),
        pages_processed=len(pages),
        message=f"Successfully extracted {len(pages)} pages and indexed {len(chunks)} chunks.",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents():
    """List all indexed documents and vector store inventory."""
    faiss_store = get_faiss_store()
    docs = faiss_store.list_documents()
    total_chunks = len(faiss_store.chunks)
    return DocumentListResponse(
        total_documents=len(docs),
        total_chunks=total_chunks,
        documents=docs,
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    admin_auth: str = Depends(verify_admin_key),
):
    """
    Delete a document and all its indexed chunks from the FAISS vector store.
    Restricted to authorized administrators.
    """
    faiss_store = get_faiss_store()
    deleted = faiss_store.delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} was not found in the index.",
        )
    return {"status": "deleted", "doc_id": doc_id, "message": "Document and all vector chunks deleted."}

