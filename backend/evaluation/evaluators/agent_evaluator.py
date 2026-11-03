"""Agent evaluator measuring intent, tool selection, escalation, and safety."""

import time
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from backend.app.agent.orchestrator import get_agent_orchestrator
from backend.app.services.session_service import get_session_service


class AgentEvaluator:
    def __init__(self):
        self.orchestrator = get_agent_orchestrator()
        self.session_service = get_session_service()

    def evaluate_case(
        self,
        test_case: Dict[str, Any],
        mock_external_tools: bool = True,
    ) -> Dict[str, Any]:
        """Execute and evaluate an agent scenario."""
        case_id = test_case.get("id")
        query = test_case.get("query")
        expected_intent = test_case.get("expected_intent")
        expected_tool = test_case.get("expected_tool")
        expected_escalated = test_case.get("expected_escalated")
        expected_keywords = test_case.get("expected_keywords", [])

        session_id = self.session_service.create_session()

        start_time = time.perf_counter()
        
        # When evaluating, mock external tools so no real customer leads or tickets are created
        if mock_external_tools:
            mock_lead = type("MockLead", (), {"id": 101, "priority": "high", "status": "new"})()
            mock_ticket = type("MockTicket", (), {"id": "TCK-101", "product_category": "Electrical", "severity": "HIGH", "status": "open"})()
            with patch("backend.app.services.lead_service.LeadService.create_lead", return_value=mock_lead), \
                 patch("backend.app.services.ticket_service.TicketService.create_ticket", return_value=(mock_ticket, "Advisory instructions")):
                response = self.orchestrator.handle_request(question=query, session_id=session_id)
        else:
            response = self.orchestrator.handle_request(question=query, session_id=session_id)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        tool_calls = response.tool_calls or []
        executed_tools = [t.get("tool") for t in tool_calls]
        intent = response.intent
        answer = response.answer
        escalated = bool(response.escalated or "whatsapp" in answer.lower())

        if expected_intent in ("PRODUCT_ENQUIRY", "TECHNICAL_SUPPORT"):
            intent_correct = intent in ("PRODUCT_ENQUIRY", "TECHNICAL_SUPPORT")
        elif expected_intent in ("QUOTATION_REQUEST", "SALES_ENQUIRY"):
            intent_correct = intent in ("QUOTATION_REQUEST", "SALES_ENQUIRY")
        elif expected_intent:
            intent_correct = (intent == expected_intent)
        else:
            intent_correct = True

        if expected_tool is None:
            tool_correct = (len(executed_tools) == 0) or ("escalate_to_human" in executed_tools and bool(expected_escalated))
        else:
            tool_correct = (expected_tool in executed_tools) or ("escalate_to_human" in executed_tools and bool(expected_escalated))

        escalation_correct = (escalated == expected_escalated) if expected_escalated is not None else True

        matched_kws = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        kw_coverage = (len(matched_kws) / len(expected_keywords)) if expected_keywords else 1.0

        # Token estimation: approx 1 token per 4 chars for prompt + answer
        estimated_tokens = int((len(query) + len(answer)) / 4)

        return {
            "id": case_id,
            "query": query,
            "predicted_intent": intent,
            "expected_intent": expected_intent,
            "intent_correct": intent_correct,
            "executed_tools": executed_tools,
            "expected_tool": expected_tool,
            "tool_correct": tool_correct,
            "escalated": escalated,
            "expected_escalated": expected_escalated,
            "escalation_correct": escalation_correct,
            "elapsed_ms": round(elapsed_ms, 2),
            "estimated_tokens": estimated_tokens,
            "keyword_coverage": round(kw_coverage, 4),
            "answer_preview": answer[:120] + ("..." if len(answer) > 120 else ""),
        }
