"""Text chunking with sliding window and metadata preservation."""

from typing import List, Tuple
from backend.app.schemas.documents import ChunkMetadata


def chunk_page_text(
    text: str,
    page_number: int,
    doc_id: str,
    source_filename: str,
    chunk_size: int = 700,
    chunk_overlap: int = 150,
) -> List[ChunkMetadata]:
    """
    Split a page's text into overlapping chunks while preserving exact page and document metadata.
    """
    if not text.strip():
        return []

    chunks: List[ChunkMetadata] = []
    start = 0
    text_len = len(text)
    chunk_index = 0

    while start < text_len:
        end = start + chunk_size
        
        # If we are not at the end of the text, try to find a natural word or sentence boundary
        if end < text_len:
            boundary = -1
            # Look for sentence boundaries (period, question mark, newline) within the last 100 chars of chunk
            search_window = text[max(start, end - 80):min(text_len, end + 40)]
            for punct in [". ", "? ", "\n", "; ", ", ", " "]:
                pos = search_window.rfind(punct)
                if pos != -1:
                    boundary = max(start, end - 80) + pos + len(punct)
                    break
            if boundary > start:
                end = boundary

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = f"{doc_id[:12]}_p{page_number}_c{chunk_index}"
            chunks.append(
                ChunkMetadata(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    source_filename=source_filename,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    char_count=len(chunk_text),
                )
            )
            chunk_index += 1

        # Move forward by (chunk_size - chunk_overlap)
        step = max(1, (end - start) - chunk_overlap)
        start += step
        if end >= text_len:
            break

    return chunks


def process_document_to_chunks(
    pages: List[Tuple[int, str]],
    doc_id: str,
    source_filename: str,
    chunk_size: int = 700,
    chunk_overlap: int = 150,
) -> List[ChunkMetadata]:
    """Process all pages of a document into an aggregated list of chunks."""
    all_chunks: List[ChunkMetadata] = []
    for page_num, page_text in pages:
        page_chunks = chunk_page_text(
            text=page_text,
            page_number=page_num,
            doc_id=doc_id,
            source_filename=source_filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(page_chunks)
    return allchunks if (allchunks := all_chunks) else []

