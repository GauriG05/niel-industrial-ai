"""FAISS vector store and document metadata manager."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import faiss
import numpy as np

from backend.app.config import get_settings
from backend.app.schemas.documents import ChunkMetadata, DocumentSummary

logger = logging.getLogger(__name__)


class FAISSStore:
    """Manages local FAISS vector indexing with metadata persistence."""

    def __init__(self, dimension: int = 1536, index_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.dimension = dimension
        if index_dir is not None:
            self.index_dir = index_dir
        elif self.settings.ENVIRONMENT == "test":
            self.index_dir = self.settings.DATA_DIR / "test_index"
        else:
            self.index_dir = self.settings.INDEX_DIR
        self.index_file = self.index_dir / "faiss.index"
        self.meta_file = self.index_dir / "metadata.json"

        # In-memory structures
        self.index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.dimension)
        self.chunks: List[ChunkMetadata] = []
        self.documents: Dict[str, DocumentSummary] = {}

        self._load()

    def _load(self):
        """Load persisted FAISS index and metadata if present."""
        if not self.index_file.exists() or not self.meta_file.exists():
            return

        try:
            self.index = faiss.read_index(str(self.index_file))
            with open(self.meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.chunks = [ChunkMetadata(**item) for item in data.get("chunks", [])]
                self.documents = {
                    doc_id: DocumentSummary(**item)
                    for doc_id, item in data.get("documents", {}).items()
                }
            logger.info("Loaded FAISS index with %d chunks and %d docs.", len(self.chunks), len(self.documents))
        except Exception as exc:
            logger.error("Failed to load existing FAISS index or metadata: %s. Starting fresh.", exc)
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            self.documents = {}

    def save(self):
        """Atomically persist FAISS index and metadata."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        # Write index to temporary file then replace
        temp_index = self.index_dir / "faiss.index.tmp"
        temp_meta = self.index_dir / "metadata.json.tmp"

        faiss.write_index(self.index, str(temp_index))
        meta_payload = {
            "chunks": [chunk.model_dump() for chunk in self.chunks],
            "documents": {doc_id: summary.model_dump() for doc_id, summary in self.documents.items()},
        }
        with open(temp_meta, "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, indent=2)

        temp_index.replace(self.index_file)
        temp_meta.replace(self.meta_file)

    def is_document_indexed(self, doc_id: str) -> bool:
        """Check if document hash is already registered."""
        return doc_id in self.documents

    def add_document_chunks(
        self,
        summary: DocumentSummary,
        chunks: List[ChunkMetadata],
        embeddings: List[List[float]],
    ):
        """Add new chunks and vectors to the index and persist."""
        if len(chunks) == 0:
            return

        vectors = np.array(embeddings, dtype=np.float32)
        # Ensure vectors are normalized for cosine similarity (Inner Product on L2-normalized vectors)
        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.chunks.extend(chunks)
        self.documents[summary.doc_id] = summary
        self.save()

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[ChunkMetadata, float]]:
        """
        Search for top_k nearest chunks using cosine similarity.
        Returns list of (ChunkMetadata, similarity_score).
        """
        if self.index.ntotal == 0 or len(self.chunks) == 0:
            return []

        q_vec = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(q_vec)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q_vec, k)

        results: List[Tuple[ChunkMetadata, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))

        return results

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document and all associated chunks.
        Rebuilds the vector index to ensure absolute consistency.
        """
        if doc_id not in self.documents:
            return False

        # Filter out chunks belonging to this doc
        surviving_chunks: List[ChunkMetadata] = []
        for chunk in self.chunks:
            if chunk.doc_id != doc_id:
                surviving_chunks.append(chunk)

        del self.documents[doc_id]

        if len(surviving_chunks) == 0:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
        else:
            # Reconstruct embeddings from remaining chunks
            from backend.app.services.openai_service import get_openai_service
            openai_service = get_openai_service()
            texts = [c.text for c in surviving_chunks]
            embeddings = openai_service.get_embeddings_batch(texts)
            
            new_index = faiss.IndexFlatIP(self.dimension)
            vectors = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(vectors)
            new_index.add(vectors)

            self.index = new_index
            self.chunks = surviving_chunks

        self.save()
        return True

    def list_documents(self) -> List[DocumentSummary]:
        """Return list of all registered documents."""
        return list(self.documents.values())

    def clear(self):
        """Completely reset the store."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunks = []
        self.documents = {}
        if self.index_file.exists():
            self.index_file.unlink()
        if self.meta_file.exists():
            self.meta_file.unlink()


_faiss_store_instance: Optional[FAISSStore] = None


def get_faiss_store(index_dir: Optional[Path] = None) -> FAISSStore:
    """Singleton accessor for FAISS vector store. If index_dir is provided, returns an instance bound to that dir."""
    global _faiss_store_instance
    if index_dir is not None:
        return FAISSStore(index_dir=index_dir)
    if _faiss_store_instance is None:
        _faiss_store_instance = FAISSStore()
    return _faiss_store_instance

