"""RAG evaluation runner executing retrieval, answer correctness, citations, and abstention benchmarks."""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.rag_service import get_rag_service
from backend.evaluation.evaluators.retrieval_evaluator import RetrievalEvaluator
from backend.evaluation.evaluators.answer_evaluator import AnswerEvaluator
from backend.evaluation.evaluators.citation_evaluator import CitationEvaluator
from backend.evaluation.evaluators.abstention_evaluator import AbstentionEvaluator

DATASET_PATH = Path(__file__).parent / "datasets" / "rag_test_cases.json"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def run_rag_evaluation(top_k: int = 5) -> Dict[str, Any]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    rag_service = get_rag_service()
    retrieval_eval = RetrievalEvaluator(top_k=top_k)
    answer_eval = AnswerEvaluator()
    citation_eval = CitationEvaluator()
    abstention_eval = AbstentionEvaluator()

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []

    print("=" * 78)
    print("NIEL RAG BENCHMARK EVALUATION SUITE")
    print(f"Loaded {len(test_cases)} verified test cases from {DATASET_PATH.name}")
    print("=" * 78)

    for tc in test_cases:
        tc_id = tc["id"]
        question = tc["question"]
        should_abstain = tc.get("should_abstain", False)

        # 1. Retrieval evaluation
        retrieval_res = retrieval_eval.evaluate_test_case(tc)

        # 2. End-to-end RAG answer generation
        start_time = time.perf_counter()
        response = rag_service.answer_question(question=question, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(elapsed_ms)

        # 3. Answer evaluation
        ans_res = answer_eval.evaluate(
            test_case=tc,
            generated_answer=response.answer,
            retrieved_contexts=retrieval_res["chunks_text"],
        )

        # 4. Citation evaluation
        cit_res = citation_eval.evaluate(
            test_case=tc,
            citations=response.citations,
        )

        # 5. Abstention evaluation
        abs_res = abstention_eval.evaluate(
            test_case=tc,
            generated_answer=response.answer,
            evidence_sufficient=response.evidence_sufficient,
        )

        # Determine overall case pass/fail
        if should_abstain:
            passed = abs_res["is_abstention_correct"]
        else:
            passed = (
                retrieval_res["recall_at_k"] >= 0.5
                and ans_res["is_correct"]
                and abs_res["is_abstention_correct"]
            )

        status_sym = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_sym} {tc_id:<9} | {tc.get('category'):<19} | {elapsed_ms:>6.1f}ms | Recall@K: {retrieval_res['recall_at_k']:.2f}")

        results.append({
            "id": tc_id,
            "category": tc.get("category"),
            "question": question,
            "passed": passed,
            "elapsed_ms": round(elapsed_ms, 2),
            "retrieval": retrieval_res,
            "answer": ans_res,
            "citation": cit_res,
            "abstention": abs_res,
        })

    # Summary metrics
    total = len(results)
    passed_cases = sum(1 for r in results if r["passed"])
    factual_cases = [r for r in results if not r["abstention"]["should_abstain"]]
    abstain_cases = [r for r in results if r["abstention"]["should_abstain"]]

    avg_recall = sum(r["retrieval"]["recall_at_k"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    avg_precision = sum(r["retrieval"]["precision_at_k"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    avg_mrr = sum(r["retrieval"]["mrr"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    avg_ndcg = sum(r["retrieval"]["ndcg_at_k"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0

    avg_correctness = sum(r["answer"]["correctness_score"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    avg_faithfulness = sum(r["answer"]["faithfulness_score"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    avg_citation = sum(r["citation"]["citation_score"] for r in factual_cases) / len(factual_cases) if factual_cases else 1.0
    abstention_accuracy = sum(1 for r in abstain_cases if r["abstention"]["is_abstention_correct"]) / len(abstain_cases) if abstain_cases else 1.0

    latencies_sorted = sorted(latencies)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies_sorted else 0.0

    summary = {
        "total_test_cases": total,
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / total, 4) if total else 0.0,
        "retrieval_metrics": {
            "mean_recall_at_k": round(avg_recall, 4),
            "mean_precision_at_k": round(avg_precision, 4),
            "mrr": round(avg_mrr, 4),
            "ndcg_at_k": round(avg_ndcg, 4),
        },
        "answer_metrics": {
            "mean_correctness": round(avg_correctness, 4),
            "mean_faithfulness": round(avg_faithfulness, 4),
            "mean_citation_accuracy": round(avg_citation, 4),
            "abstention_accuracy": round(abstention_accuracy, 4),
        },
        "performance": {
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
        },
    }

    report = {
        "benchmark": "NIEL RAG Reliability Benchmark",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "top_k": top_k,
        "summary": summary,
        "detailed_results": results,
    }

    report_path = REPORT_DIR / "rag_evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 78)
    print("RAG BENCHMARK SUMMARY")
    print(f"Total: {total} | Passed: {passed_cases} ({summary['pass_rate']*100:.1f}%)")
    print(f"Recall@{top_k}: {avg_recall:.2f} | Precision@{top_k}: {avg_precision:.2f} | MRR: {avg_mrr:.2f} | nDCG@{top_k}: {avg_ndcg:.2f}")
    print(f"Answer Correctness: {avg_correctness*100:.1f}% | Faithfulness: {avg_faithfulness*100:.1f}% | Citation Acc: {avg_citation*100:.1f}%")
    print(f"Abstention Accuracy: {abstention_accuracy*100:.1f}% | Latency (avg/p95): {avg_latency:.1f}ms / {p95_latency:.1f}ms")
    print(f"Saved machine-readable report to: {report_path}")
    print("=" * 78 + "\n")

    return report


if __name__ == "__main__":
    run_rag_evaluation()

