"""Answer evaluator checking correctness and faithfulness of RAG answers."""

from typing import Any, Dict, Sequence
from backend.evaluation.metrics.answer_metrics import (
    evaluate_answer_correctness,
    evaluate_faithfulness,
)


class AnswerEvaluator:
    def evaluate(
        self,
        test_case: Dict[str, Any],
        generated_answer: str,
        retrieved_contexts: Sequence[str],
    ) -> Dict[str, Any]:
        """Evaluate answer correctness against keywords/facts and faithfulness to context."""
        expected_keywords = test_case.get("expected_answer_keywords", [])
        reference_facts = test_case.get("reference_facts", [])

        correctness = evaluate_answer_correctness(
            generated_answer=generated_answer,
            expected_keywords=expected_keywords,
            reference_facts=reference_facts,
        )

        faithfulness = evaluate_faithfulness(
            generated_answer=generated_answer,
            retrieved_contexts=retrieved_contexts,
        )

        return {
            "correctness_score": correctness["score"],
            "is_correct": correctness["is_correct"],
            "keyword_coverage": correctness["keyword_coverage"],
            "matched_keywords": correctness["matched_keywords"],
            "missing_keywords": correctness["missing_keywords"],
            "faithfulness_score": faithfulness["score"],
            "is_faithful": faithfulness["is_faithful"],
            "unsupported_claims": faithfulness["unsupported_claims"],
        }

