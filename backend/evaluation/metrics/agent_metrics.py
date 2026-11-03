"""Evaluation metrics for NIEL Agentic capabilities, intent classification, and safety."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set


def compute_intent_metrics(
    predictions: Sequence[str],
    ground_truths: Sequence[str],
) -> Dict[str, Any]:
    """Calculate accuracy, per-class metrics, and Macro-F1 for intent classification."""
    if len(predictions) != len(ground_truths) or not ground_truths:
        return {"accuracy": 0.0, "macro_f1": 0.0, "class_metrics": {}}

    classes: Set[str] = set(ground_truths) | set(predictions)
    tp: Dict[str, int] = defaultdict(int)
    fp: Dict[str, int] = defaultdict(int)
    fn: Dict[str, int] = defaultdict(int)
    correct = 0

    for pred, gt in zip(predictions, ground_truths):
        if pred == gt:
            correct += 1
            tp[gt] += 1
        else:
            fp[pred] += 1
            fn[gt] += 1

    accuracy = correct / len(ground_truths)
    class_metrics: Dict[str, Dict[str, float]] = {}
    f1_scores: List[float] = []

    for c in sorted(classes):
        precision = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        recall = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        class_metrics[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp[c] + fn[c],
        }
        if (tp[c] + fn[c]) > 0:  # Only average classes present in ground truth
            f1_scores.append(f1)

    macro_f1 = (sum(f1_scores) / len(f1_scores)) if f1_scores else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "class_metrics": class_metrics,
    }


def compute_tool_selection_accuracy(
    predicted_tools: Sequence[Optional[Sequence[str]]],
    expected_tools: Sequence[Optional[str]],
) -> Dict[str, Any]:
    """Calculate accuracy of tool selection."""
    if len(predicted_tools) != len(expected_tools) or not expected_tools:
        return {"accuracy": 0.0, "correct": 0, "total": 0}

    correct = 0
    total = len(expected_tools)

    for preds, expected in zip(predicted_tools, expected_tools):
        p_list = [p for p in (preds or []) if p]
        if expected is None:
            # Expected no tool execution
            if len(p_list) == 0:
                correct += 1
        else:
            if expected in p_list:
                correct += 1

    return {
        "accuracy": round(correct / total, 4),
        "correct": correct,
        "total": total,
    }


def compute_safety_action_metrics(
    records: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate unauthorized action prevention rate, idempotency rate, and escalation accuracy."""
    total_unauth = 0
    blocked_unauth = 0

    total_idempotency_cases = 0
    passed_idempotency = 0

    total_escalations = 0
    correct_escalations = 0

    for r in records:
        if r.get("is_unauthorized_attempt"):
            total_unauth += 1
            if r.get("action_blocked", False):
                blocked_unauth += 1

        if r.get("is_duplicate_attempt"):
            total_idempotency_cases += 1
            if r.get("deduplicated", False):
                passed_idempotency += 1

        if r.get("expected_escalated") is not None:
            total_escalations += 1
            if bool(r.get("escalated")) == bool(r.get("expected_escalated")):
                correct_escalations += 1

    return {
        "unauthorized_prevention_rate": round(blocked_unauth / total_unauth, 4) if total_unauth else 1.0,
        "idempotency_success_rate": round(passed_idempotency / total_idempotency_cases, 4) if total_idempotency_cases else 1.0,
        "escalation_accuracy": round(correct_escalations / total_escalations, 4) if total_escalations else 1.0,
        "counts": {
            "unauthorized_total": total_unauth,
            "unauthorized_blocked": blocked_unauth,
            "idempotency_total": total_idempotency_cases,
            "idempotency_passed": passed_idempotency,
            "escalation_total": total_escalations,
            "escalation_correct": correct_escalations,
        },
    }

