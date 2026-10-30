"""Automated RAG evaluation harness for NIEL Industrial Intelligence Assistant."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.rag_service import get_rag_service
from backend.app.retrieval.retriever import get_retriever

QUESTIONS_FILE = Path(__file__).parent / "questions.json"


def run_evaluation() -> Dict[str, Any]:
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    rag_service = get_rag_service()
    retriever = get_retriever()

    results: List[Dict[str, Any]] = []
    total_latency_ms = 0.0

    retrieval_hits = 0
    grounded_hits = 0
    citation_hits = 0
    abstention_hits = 0

    total_evaluable_retrieval = 0
    total_evaluable_abstention = 0

    print("=" * 78)
    print("NIEL INDUSTRIAL INTELLIGENCE AI - AUTOMATED EVALUATION SUITE")
    print("=" * 78)
    print(f"Loaded {len(test_cases)} manually verified evaluation inquiries.\n")

    for tc in test_cases:
        q_id = tc["id"]
        question = tc["question"]
        expected_page = tc.get("expected_page")
        should_abstain = tc["should_abstain"]
        expected_keywords = tc["expected_answer_keywords"]

        start_time = time.perf_counter()
        response = rag_service.answer_question(question=question, top_k=5)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        total_latency_ms += elapsed_ms

        answer = response.answer
        citations = response.citations
        is_sufficient = response.evidence_sufficient

        # 1. Retrieval & Citation Verification
        retrieval_ok = False
        citation_ok = False
        if expected_page is not None:
            total_evaluable_retrieval += 1
            # Check if expected page is present in citations
            retrieval_ok = any(c.page_number == expected_page for c in citations)
            citation_ok = retrieval_ok
            if retrieval_ok:
                retrieval_hits += 1
                citation_hits += 1

        # 2. Grounded Answer Correctness
        answer_ok = any(kw.lower() in answer.lower() for kw in expected_keywords)
        if answer_ok and not should_abstain:
            grounded_hits += 1

        # 3. Abstention Correctness
        abstention_ok = False
        if should_abstain:
            total_evaluable_abstention += 1
            abstention_ok = (not is_sufficient) and answer_ok
            if abstention_ok:
                abstention_hits += 1

        test_passed = (abstention_ok if should_abstain else (answer_ok and citation_ok))

        results.append({
            "id": q_id,
            "category": tc["category"],
            "question": question,
            "passed": test_passed,
            "latency_ms": round(elapsed_ms, 2),
            "evidence_sufficient": is_sufficient,
            "citations_count": len(citations),
            "answer_preview": answer[:80] + "..." if len(answer) > 80 else answer,
        })

        status_symbol = "PASS" if test_passed else "FAIL"
        print(f"[{status_symbol}] {q_id}: {question[:50]}... ({elapsed_ms:.1f}ms)")

    # Aggregate Metrics
    recall_at_k = (retrieval_hits / total_evaluable_retrieval) * 100 if total_evaluable_retrieval else 0.0
    citation_accuracy = (citation_hits / total_evaluable_retrieval) * 100 if total_evaluable_retrieval else 0.0
    abstention_accuracy = (abstention_hits / total_evaluable_abstention) * 100 if total_evaluable_abstention else 0.0
    overall_accuracy = (sum(1 for r in results if r["passed"]) / len(test_cases)) * 100
    avg_latency = total_latency_ms / len(test_cases)

    summary = {
        "total_test_cases": len(test_cases),
        "overall_accuracy_pct": round(overall_accuracy, 2),
        "recall_at_5_pct": round(recall_at_k, 2),
        "citation_accuracy_pct": round(citation_accuracy, 2),
        "abstention_accuracy_pct": round(abstention_accuracy, 2),
        "average_latency_ms": round(avg_latency, 2),
        "results": results,
    }

    print("\n" + "=" * 78)
    print("EVALUATION BENCHMARK SUMMARY")
    print("=" * 78)
    print(f"Overall Accuracy:       {summary['overall_accuracy_pct']}%")
    print(f"Recall@5 (Supported):   {summary['recall_at_5_pct']}%")
    print(f"Citation Correctness:   {summary['citation_accuracy_pct']}%")
    print(f"Abstention Accuracy:    {summary['abstention_accuracy_pct']}%")
    print(f"Average Latency:        {summary['average_latency_ms']} ms")
    print("=" * 78)

    return summary


if __name__ == "__main__":
    run_evaluation()
