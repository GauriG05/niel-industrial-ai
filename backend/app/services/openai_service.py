"""OpenAI client wrapper for embeddings and generation with cost tracking & offline fallback."""

import hashlib
import logging
from typing import Dict, List, Optional
import numpy as np
from openai import OpenAI, OpenAIError

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# Approximate pricing per 1,000,000 tokens (USD)
EMBEDDING_COST_PER_MILLION = 0.020  # text-embedding-3-small
GPT4O_MINI_PROMPT_PER_MILLION = 0.150
GPT4O_MINI_COMPLETION_PER_MILLION = 0.600


class OpenAIService:
    """Wrapper around official OpenAI SDK with caching and test fallback."""

    def __init__(self):
        self.settings = get_settings()
        self._embedding_cache: Dict[str, List[float]] = {}
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_embedding_tokens = 0

    @property
    def is_live_configured(self) -> bool:
        """Check if an active OpenAI API key is supplied."""
        key = self.settings.OPENAI_API_KEY.strip()
        return bool(key and not key.startswith("mock-") and not key.startswith("sk-your-"))

    def _get_client(self) -> OpenAI:
        if not self.is_live_configured:
            raise OpenAIError("OpenAI API key is not configured or is a mock key.")
        return OpenAI(api_key=self.settings.OPENAI_API_KEY)

    def _generate_deterministic_embedding(self, text: str, dimensions: int = 1536) -> List[float]:
        """
        Deterministic term-frequency feature hashing for offline testing without API spending.
        Maps n-grams into vector space so text sharing words/stems has positive cosine similarity.
        """
        vec = np.zeros(dimensions, dtype=np.float32)
        words = [w.lower().strip(".,;:!?'\"()[]{}") for w in text.split() if len(w) > 2]
        
        for w in words:
            # Hash single word
            idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % dimensions
            vec[idx] += 2.0
            
            # Bigram hashing for sub-phrase semantic affinity
            for i in range(len(w) - 3):
                gram = w[i:i+4]
                g_idx = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16) % dimensions
                vec[g_idx] += 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for a single string with in-memory caching."""
        cache_key = hashlib.sha256(f"{self.settings.OPENAI_EMBEDDING_MODEL}:{text}".encode()).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.is_live_configured:
            # Safe offline deterministic embedding for tests and local init
            vec = self._generate_deterministic_embedding(text)
            self._embedding_cache[cache_key] = vec
            return vec

        client = self._get_client()
        try:
            response = client.embeddings.create(
                model=self.settings.OPENAI_EMBEDDING_MODEL,
                input=text,
            )
            vec = response.data[0].embedding
            self._embedding_cache[cache_key] = vec
            if hasattr(response, "usage") and response.usage:
                self.total_embedding_tokens += response.usage.total_tokens
            return vec
        except OpenAIError as exc:
            logger.error("OpenAI Embedding generation failed: %s", exc)
            raise

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation with caching."""
        return [self.get_embedding(t) for t in texts]

    def estimate_cost(self) -> float:
        """Estimate cumulative USD spend in this session."""
        embed_cost = (self.total_embedding_tokens / 1_000_000.0) * EMBEDDING_COST_PER_MILLION
        prompt_cost = (self.total_prompt_tokens / 1_000_000.0) * GPT4O_MINI_PROMPT_PER_MILLION
        completion_cost = (self.total_completion_tokens / 1_000_000.0) * GPT4O_MINI_COMPLETION_PER_MILLION
        return round(embed_cost + prompt_cost + completion_cost, 6)


_openai_service_instance: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    """Singleton accessor for OpenAI service."""
    global _openai_service_instance
    if _openai_service_instance is None:
        _openai_service_instance = OpenAIService()
    return _openai_service_instance
