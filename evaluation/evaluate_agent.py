"""Automated multi-dimensional evaluation suite for NIEL Agentic Support System."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent.orchestrator import get_agent_orchestrator
from backend.app.services.session_service import get_session_service

AGENT_CASES_FILE = Path(__file__).parent / "agent_test_cases.json"


def run_agent_evaluation() -> Dict[str, Any]:
    with open(AGENT_CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    orchestrator = get_agent_orchestrator()
    session_service = get_session_service()

    results: List[Dict[str, Any]] = []
    total_latency_ms = 0.0

    intent_matches = 0
    tool_matches = 0
    safety_matches = 0
    total_safety_cases = 0

    print("=" * 82)
    print("NIEL AGENTIC CUSTOMER SUPPORT SYSTEM - AUTOMATED EVALUATION SUITE")
    print("=" * 82)
    print(f"Executing {len(cases)} multi-dimensional agent evaluation scenarios...\n")

    for tc in cases:
        case_id = tc["id"]
        category = tc["category"]
        query = tc["query"]
        expected_intent = tc.get("expected_intent")
        expected_tool = tc.get("expected_tool")
        expected_escalated = tc.get("expected_escalated")
        expected_ticket = tc.get("expected_ticket")
        expected_lead = tc.get("expected_lead")
        expected_keywords = tc.get("expected_keywords", [])

        # Fresh session for isolated scenario
        session_id = session_service.create_session()

        start_time = time.perf_counter()
        response = orchestrator.handle_request(question=query, session_id=session_id)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        total_latency_ms += elapsed_ms

        answer = response.answer
        intent = response.intent
        tool_names = [t.get("tool") for t in (response.tool_calls or [])]

        # 1. Intent Match
        intent_ok = (intent == expected_intent) if expected_intent else True
        if intent_ok:
            intent_matches += 1

        # 2. Tool Selection Match
        tool_ok = True
        if expected_tool:
            tool_ok = expected_tool in tool_names
            if tool_ok:
                tool_matches += 1

        # 3. Safety Guardrail & Escalation Match
        safety_ok = True
        if expected_escalated is not None:
            total_safety_cases += 1
            safety_ok = (response.escalated == expected_escalated)
            if safety_ok:
                safety_matches += 1

        # 4. Ticket / Lead Match
        ticket_ok = (response.ticket_id is not None) if expected_ticket else True
        lead_ok = (response.lead_id is not None) if expected_lead else True

        # 5. Content Keyword Match
        keyword_ok = any(kw.lower() in answer.lower() for kw in expected_keywords) if expected_keywords else True

        scenario_passed = intent_ok and tool_ok and safety_ok and ticket_ok and lead_ok and keyword_ok

        results.append({
            "id": case_id,
            "category": category,
            "passed": scenario_passed,
            "intent": intent,
            "tools": tool_names,
            "latency_ms": round(elapsed_ms, 2),
            "ticket_id": response.ticket_id,
            "lead_id": response.lead_id,
            "escalated": response.escalated,
        })

        status_str = "PASS" if scenario_passed else "FAIL"
        print(f"[{status_str}] {case_id} ({category}): Intent='{intent}', Tools={tool_names} ({elapsed_ms:.1f}ms)")

    # Compute Metrics
    num_cases = len(cases)
    intent_acc = (intent_matches / num_cases) * 100.0
    tool_acc = (tool_matches / sum(1 for c in cases if "expected_tool" in c)) * 100.0
    safety_acc = (safety_matches / total_safety_cases * 100.0) if total_safety_cases else 100.0
    avg_latency = total_latency_ms / num_cases
    passed_cases = sum(1 for r in results if r["passed"])
    overall_acc = (passed_cases / num_cases) * 100.0

    print("\n" + "=" * 82)
    print("EVALUATION SUMMARY REPORT")
    print("=" * 82)
    print(f"Overall Benchmark Accuracy  : {overall_acc:.1f}% ({passed_cases}/{num_cases} passed)")
    print(f"Intent Classification Rate  : {intent_acc:.1f}% ({intent_matches}/{num_cases})")
    print(f"Tool Selection Accuracy     : {tool_acc:.1f}%")
    print(f"Safety Compliance Rate      : {safety_acc:.1f}%")
    print(f"Average System Latency      : {avg_latency:.2f} ms")
    print("=" * 82 + "\n")

    return {
        "overall_accuracy": overall_acc,
        "intent_accuracy": intent_acc,
        "tool_accuracy": tool_acc,
        "safety_compliance": safety_acc,
        "average_latency_ms": avg_latency,
        "results": results,
    }


if __name__ == "__main__":
    report = run_agent_evaluation()
    if report["overall_accuracy"] < 80.0:
        sys.exit(1)

