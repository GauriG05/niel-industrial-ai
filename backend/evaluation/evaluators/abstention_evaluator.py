"""Abstention evaluator verifying that the system refrains from hallucinating."""

from typing import Any, Dict
from backend.evaluation.metrics.answer_metrics import evaluate_abstention


class AbstentionEvaluator:
    def evaluate(
        self,
        test_case: Dict[str, Any],
        generated_answer: str,
        evidence_sufficient: bool,
    ) -> Dict[str, Any]:
        """Evaluate if system abstained properly when required."""
        should_abstain = test_case.get("should_abstain", False)

        res = evaluate_abstention(
            should_abstain=should_abstain,
            generated_answer=generated_answer,
            evidence_sufficient=evidence_sufficient,
        )
        return {
            "should_abstain": should_abstain,
            "detected_abstention": res["detected_abstention"],
            "evidence_sufficient": evidence_sufficient,
            "is_abstention_correct": res["is_correct"],
        }
