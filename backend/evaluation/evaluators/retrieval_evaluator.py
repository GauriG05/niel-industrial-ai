"""Retrieval evaluator measuring Recall@K, Precision@K, MRR, and nDCG@K."""

from typing import Any, Dict, List, Sequence
from backend.app.retrieval.retriever import get_retriever
from backend.evaluation.metrics.retrieval_metrics import (
    recall_at_k,
    precision_at_k,
    reciprocal_rank,
    ndcg_at_k,
)


class RetrievalEvaluator:
    def __init__(self, top_k: int = 5):
        self.top_k = top_k
        self.retriever = get_retriever()

    def evaluate_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate retrieval performance for a single test case."""
        question = test_case["question"]
        expected_sources = test_case.get("expected_sources", [])
        expected_pages = test_case.get("expected_pages", [])
        should_abstain = test_case.get("should_abstain", False)

        results = self.retriever.retrieve(query=question, top_k=self.top_k)
        retrieved_chunks = [item[0] if isinstance(item, tuple) else item for item in results]

        retrieved_sources = [c.source_filename for c in retrieved_chunks]
        retrieved_pages = [c.page_number for c in retrieved_chunks]

        # For retrieval metrics on documents, consider source filenames
        rec_k = recall_at_k(retrieved_sources, expected_sources, k=self.top_k)
        prec_k = precision_at_k(retrieved_sources, expected_sources, k=self.top_k)
        mrr = reciprocal_rank(retrieved_sources, expected_sources)
        ndcg = ndcg_at_k(retrieved_sources, expected_sources, k=self.top_k)

        # Check page hits
        page_hit = False
        if expected_pages:
            page_hit = any(p in expected_pages for p in retrieved_pages)
        else:
            page_hit = True

        return {
            "test_case_id": test_case.get("id"),
            "question": question,
            "top_k": self.top_k,
            "retrieved_count": len(retrieved_chunks),
            "retrieved_sources": retrieved_sources,
            "retrieved_pages": retrieved_pages,
            "recall_at_k": round(rec_k, 4),
            "precision_at_k": round(prec_k, 4),
            "mrr": round(mrr, 4),
            "ndcg_at_k": round(ndcg, 4),
            "page_hit": page_hit,
            "chunks_text": [c.text for c in retrieved_chunks],
        }
