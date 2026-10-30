"""Document text extraction with validation and scanned PDF detection."""

import io
from typing import Dict, List, Tuple
from pypdf import PdfReader


class ExtractionError(Exception):
    """Raised when document extraction fails or file is invalid."""
    pass


class ScannedDocumentError(ExtractionError):
    """Raised when PDF contains pages but negligible extractable text (likely image/scan)."""
    pass


def validate_pdf_content(content: bytes) -> bool:
    """Validate that raw bytes start with valid PDF magic bytes '%PDF-'."""
    return content.startswith(b"%PDF-")


def extract_pages_from_pdf(content: bytes) -> List[Tuple[int, str]]:
    """
    Extract text page-by-page from PDF bytes.
    Returns a list of tuples: (page_number_1_indexed, text_content).
    Raises ScannedDocumentError if PDF has negligible extractable text.
    """
    if not validate_pdf_content(content):
        raise ExtractionError("File does not start with valid PDF magic bytes (%PDF-).")

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"Failed to parse PDF structure: {str(exc)}") from exc

    if len(reader.pages) == 0:
        raise ExtractionError("The PDF contains 0 pages.")

    pages_text: List[Tuple[int, str]] = []
    total_characters = 0

    for idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        
        normalized = " ".join(page_text.split())
        pages_text.append((idx, normalized))
        total_characters += len(normalized)

    # Scanned PDF detection heuristic: if average chars per page < 40 or total chars < 30
    if len(reader.pages) > 0 and (total_characters / len(reader.pages) < 20 or total_characters < 30):
        raise ScannedDocumentError(
            f"PDF has {len(reader.pages)} page(s) but only {total_characters} text characters were extractable. "
            "This document appears to be a scanned image without an embedded text layer. "
            "Optical Character Recognition (OCR) is required before indexing."
        )

    return pages_text


def extract_text_from_plain(content: bytes, filename: str) -> List[Tuple[int, str]]:
    """Extract text from plain text or markdown files as a single page (page 1)."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            raise ExtractionError(f"Failed to decode text file: {str(exc)}") from exc

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        raise ExtractionError("Plain text document is empty.")

    return [(1, normalized)]

