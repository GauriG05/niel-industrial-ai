"""Citation evaluator verifying source attribution and page numbers."""

from typing import Any, Dict, Sequence
from backend.evaluation.metrics.answer_metrics import evaluate_citation_accuracy


class CitationEvaluator:
    def evaluate(
        self,
        test_case: Dict[str, Any],
        citations: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate citations against expected sources and pages."""
        expected_sources = test_case.get("expected_sources", [])
        expected_pages = test_case.get("expected_pages", [])

        res = evaluate_citation_accuracy(
            citations=citations,
            expected_sources=expected_sources,
            expected_pages=expected_pages,
        )
        return {
            "citation_score": res["score"],
            "source_hit": res["source_hit"],
            "page_hit": res["page_hit"],
            "cited_sources": res["cited_sources"],
            "cited_pages": res["cited_pages"],
        }

