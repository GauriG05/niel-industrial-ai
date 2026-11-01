"""Text chunking with sliding window, table preservation, and category metadata extraction."""

import re
from typing import List, Optional, Tuple
from backend.app.schemas.documents import ChunkMetadata


def detect_document_category(filename: str, text_sample: str = "") -> Optional[str]:
    """Infer product category from filename or header patterns."""
    fname = filename.lower()
    sample = text_sample.lower()

    if "ac motor" in fname or "ac_motor" in fname or "motors_catalogue" in fname:
        return "AC Motors"
    elif "dc motor" in fname or "dc_motor" in fname:
        return "DC Motors"
    elif "pump" in fname or "valve" in fname:
        return "Pumps and Valves"
    elif "transformer" in fname:
        return "Transformers"
    elif "switchgear" in fname or "panel" in fname:
        return "Switchgear"
    elif "substation" in fname:
        return "Substation Systems"
    elif "company" in fname or "catalog" in fname or "intro" in fname:
        if "category: switchgear" in sample:
            return "Switchgear"
        if "category: transformers" in sample:
            return "Transformers"
        if "category: pumps" in sample:
            return "Pumps and Valves"
        if "category: motors" in sample:
            return "AC Motors"
        return "Company Information"
    return None


def extract_active_heading(text: str) -> Optional[str]:
    """Extract section heading or product title from chunk content."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:3]:
        if line.startswith(("PRODUCT:", "CATEGORY:", "RANGE:", "#", "##", "###")):
            clean = re.sub(r"^(PRODUCT:|CATEGORY:|RANGE:|#+\s*)", "", line).strip()
            return clean[:80]
    return None


def chunk_page_text(
    text: str,
    page_number: int,
    doc_id: str,
    source_filename: str,
    chunk_size: int = 700,
    chunk_overlap: int = 150,
    category: Optional[str] = None,
) -> List[ChunkMetadata]:
    """
    Split a page's text into overlapping chunks while preserving headings,
    tables, category, and exact page metadata.
    """
    if not text.strip():
        return []

    doc_category = category or detect_document_category(source_filename, text[:300])
    chunks: List[ChunkMetadata] = []
    start = 0
    text_len = len(text)
    chunk_index = 0

    while start < text_len:
        end = start + chunk_size
        
        # If we are not at the end of the text, try to find a natural boundary
        if end < text_len:
            boundary = -1
            # Look for paragraph breaks, table row breaks, or sentence ends
            search_window = text[max(start, end - 100):min(text_len, end + 50)]
            for punct in ["\n\n", "\n", ". ", "? ", "; ", ", ", " "]:
                pos = search_window.rfind(punct)
                if pos != -1:
                    boundary = max(start, end - 100) + pos + len(punct)
                    break
            if boundary > start:
                end = boundary

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunk_id = f"{doc_id[:12]}_p{page_number}_c{chunk_index}"
            heading = extract_active_heading(chunk_text)
            chunks.append(
                ChunkMetadata(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    source_filename=source_filename,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    char_count=len(chunk_text),
                    category=doc_category,
                    heading=heading,
                )
            )
            chunk_index += 1

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
    category: Optional[str] = None,
) -> List[ChunkMetadata]:
    """Process all pages of a document into an aggregated list of chunks with category metadata."""
    doc_category = category or detect_document_category(source_filename)
    all_chunks: List[ChunkMetadata] = []
    for page_num, page_text in pages:
        page_chunks = chunk_page_text(
            text=page_text,
            page_number=page_num,
            doc_id=doc_id,
            source_filename=source_filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            category=doc_category,
        )
        all_chunks.extend(page_chunks)
    return allchunks if (allchunks := all_chunks) else []
