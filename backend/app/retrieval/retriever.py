"""Independent retrieval service for query vector search and relevance filtering."""

import logging
from typing import List, Tuple
from backend.app.config import get_settings
from backend.app.schemas.documents import ChunkMetadata
from backend.app.services.openai_service import get_openai_service
from backend.app.retrieval.faiss_store import get_faiss_store

logger = logging.getLogger(__name__)


class Retriever:
    """Independent retrieval service for semantic similarity search."""

    def __init__(self):
        self.settings = get_settings()
        self.openai_service = get_openai_service()
        self.faiss_store = get_faiss_store()

    def normalize_query(self, query: str) -> str:
        """Sanitize and normalize query string."""
        return " ".join(query.strip().split())

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = None,
    ) -> List[Tuple[ChunkMetadata, float]]:
        """
        Retrieve relevant document chunks with similarity score above threshold.
        Returns list of (ChunkMetadata, similarity_score).
        """
        normalized_q = self.normalize_query(query)
        if not normalized_q:
            return []

        if threshold is None:
            # If running live OpenAI embeddings, use configured threshold (0.35)
            # If running offline test embeddings, use lower threshold (0.015)
            if self.openai_service.is_live_configured:
                threshold = self.settings.SIMILARITY_SCORE_THRESHOLD
            else:
                threshold = 0.015

        # Generate query vector
        query_vector = self.openai_service.get_embedding(normalized_q)

        # Vector search in FAISS store
        raw_results = self.faiss_store.search(query_vector=query_vector, top_k=top_k)

        # Relevance filtering
        filtered_results: List[Tuple[ChunkMetadata, float]] = []
        for chunk, score in raw_results:
            if score >= threshold:
                filtered_results.append((chunk, score))
            else:
                logger.debug(
                    "Filtered out chunk %s with score %.3f below threshold %.3f",
                    chunk.chunk_id,
                    score,
                    threshold,
                )

        return filtered_results


_retriever_instance = None


def get_retriever() -> Retriever:
    """Singleton accessor for Retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    return _retriever_instance
