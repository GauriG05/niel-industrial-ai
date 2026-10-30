"""Schemas for document ingestion, chunks, and metadata management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata associated with an indexed chunk of text."""
    chunk_id: str = Field(..., description="Unique chunk identifier, e.g. doc_id_chunk_idx")
    doc_id: str = Field(..., description="SHA-256 hash or unique ID of the source document")
    source_filename: str = Field(..., description="Original filename of the document")
    page_number: int = Field(..., description="1-indexed source document page number")
    chunk_index: int = Field(..., description="Zero-indexed sequence number of the chunk")
    text: str = Field(..., description="The chunk text payload")
    char_count: int = Field(..., description="Character length of chunk text")


class DocumentSummary(BaseModel):
    """Summary of an indexed document."""
    doc_id: str = Field(..., description="SHA-256 hash identifier")
    filename: str = Field(..., description="Source document filename")
    page_count: int = Field(..., description="Total pages processed")
    chunk_count: int = Field(..., description="Total chunks indexed into vector store")
    created_at: str = Field(..., description="ISO 8601 timestamp of indexing")
    file_size_bytes: int = Field(..., description="File size in bytes")


class IngestionResponse(BaseModel):
    """Response returned upon successful document ingestion."""
    status: str = Field(default="indexed", description="Ingestion status: indexed, duplicate_skipped, or rejected")
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Filename")
    chunks_indexed: int = Field(..., description="Number of chunks added to FAISS")
    pages_processed: int = Field(..., description="Total pages extracted")
    message: str = Field(..., description="Human-readable result explanation")


class DocumentListResponse(BaseModel):
    """List of all indexed documents."""
    total_documents: int
    total_chunks: int
    documents: List[DocumentSummary]

