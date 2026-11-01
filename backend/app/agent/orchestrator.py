"""Agent Orchestrator: manages customer intent, multi-turn context, tool execution, and grounded replies."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.app.agent.tools import AGENT_TOOLS_SCHEMA, get_tool_dispatcher
from backend.app.schemas.chat import ChatResponse, Citation, UsageMetadata
from backend.app.schemas.intent import CustomerIntent
from backend.app.services.customer_service import get_customer_service
from backend.app.services.intent_service import get_intent_service
from backend.app.services.openai_service import OpenAIService
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import get_session_service

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates customer intent analysis, memory injection, tool calling, and grounded answers."""

    def __init__(
        self,
        intent_service=None,
        tool_dispatcher=None,
        rag_service=None,
        session_service=None,
        customer_service=None,
        openai_service=None,
    ):
        self.intent_service = intent_service or get_intent_service()
        self.tool_dispatcher = tool_dispatcher or get_tool_dispatcher()
        self.rag_service = rag_service or get_rag_service()
        self.session_service = session_service or get_session_service()
        self.customer_service = customer_service or get_customer_service()
        self.openai_service = openai_service or OpenAIService()

    def _resolve_customer_id(self, session_id: Optional[str], customer_id: Optional[str]) -> Optional[str]:
        """Resolve active customer ID from parameter or session store."""
        if customer_id:
            return customer_id
        if session_id:
            return self.session_service.get_session_customer_id(session_id)
        return None

    def handle_request(
        self,
        question: str,
        session_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 4,
    ) -> ChatResponse:
        """Process incoming user question through intent classification and agent tool orchestration."""
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        cid = self._resolve_customer_id(session_id, customer_id)

        # 0. Check emergency kill switch & prompt injection defenses
        if self.rag_service.settings.KILL_SWITCH_ENABLED:
            return self.rag_service.answer_question(
                question=question,
                top_k=top_k,
                conversation_history=conversation_history,
                session_id=session_id,
            )

        q_lower = question.lower()
        injection_triggers = [
            "ignore previous instructions",
            "system prompt",
            "developer prompt",
            "reveal instructions",
            "api key",
            "api_key",
            "bypass guardrails",
            "jailbreak",
        ]
        if any(trigger in q_lower for trigger in injection_triggers):
            return self.rag_service.answer_question(
                question=question,
                top_k=top_k,
                conversation_history=conversation_history,
                session_id=session_id,
            )

        # 1. Server-side session history resolution
        effective_history = conversation_history or []
        if session_id and not effective_history:
            effective_history = self.session_service.get_recent_history(session_id, max_turns=8)

        # 2. Intent Classification
        intent_result = self.intent_service.classify_intent(question, effective_history)
        logger.info("Classified intent: %s (confidence=%.2f, escalation=%s)", 
                    intent_result.intent.value, intent_result.confidence, intent_result.requires_escalation)

        executed_tools: List[Dict[str, Any]] = []
        ticket_id: Optional[str] = None
        lead_id: Optional[int] = None
        is_escalated: bool = False

        # 3. Path: Explicit Human Escalation or Critical Safety Hazard
        if intent_result.requires_escalation:
            is_escalated = True
            esc_res = self.tool_dispatcher.execute_tool(
                "escalate_to_human",
                {"reason": intent_result.reasoning or "Immediate escalation required"},
                session_id=session_id,
                customer_id=cid,
            )
            executed_tools.append({"tool": "escalate_to_human", "output": esc_res})

            if intent_result.detected_entities.get("safety_hazard_detected"):
                # Automatically generate a critical support ticket
                prod_cat = intent_result.detected_entities.get("product_category", "Electrical Equipment")
                ticket_res = self.tool_dispatcher.execute_tool(
                    "create_support_ticket",
                    {
                        "product_category": prod_cat,
                        "issue_description": question,
                        "severity": "CRITICAL",
                    },
                    session_id=session_id,
                    customer_id=cid,
                )
                executed_tools.append({"tool": "create_support_ticket", "output": ticket_res})
                ticket_id = ticket_res.get("ticket_id")

                answer_text = (
                    "CRITICAL SAFETY WARNING: Do not attempt uncertified DIY maintenance or live circuit adjustments "
                    "on high-voltage electrical equipment. Immediately isolate power at the main breaker/switchboard.\n\n"
                    f"A critical support ticket ({ticket_id}) has been created, and our engineering team is taking over "
                    "this session immediately."
                )
            else:
                answer_text = (
                    "I have connected this conversation with a live NIEL technical representative. "
                    "An engineer will assist you shortly on this channel."
                )

            return ChatResponse(
                answer=answer_text,
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
                intent=intent_result.intent.value,
                tool_calls=executed_tools,
                ticket_id=ticket_id,
                lead_id=lead_id,
                escalated=is_escalated,
            )

        # 4. Path: Complaint / Fault Report -> Create Support Ticket
        if intent_result.intent == CustomerIntent.COMPLAINT:
            prod_cat = intent_result.detected_entities.get("product_category", "Industrial Equipment")
            ticket_res = self.tool_dispatcher.execute_tool(
                "create_support_ticket",
                {
                    "product_category": prod_cat,
                    "issue_description": question,
                    "severity": intent_result.detected_entities.get("urgency", "MEDIUM"),
                },
                session_id=session_id,
                customer_id=cid,
            )
            executed_tools.append({"tool": "create_support_ticket", "output": ticket_res})
            ticket_id = ticket_res.get("ticket_id")
            safety_warning = ticket_res.get("safety_advisory")

            # Also search knowledge base for troubleshooting guidance
            search_res = self.tool_dispatcher.execute_tool(
                "search_product_knowledge",
                {"query": f"{prod_cat} troubleshooting {question}", "top_k": 3},
                session_id=session_id,
                customer_id=cid,
            )
            executed_tools.append({"tool": "search_product_knowledge", "output": search_res})

            answer_parts = []
            if safety_warning:
                answer_parts.append(safety_warning)
            answer_parts.append(
                f"Your support ticket **{ticket_id}** has been registered with NIEL Customer Service. "
                "Our service engineering team will review the operating data and contact you."
            )
            answer_text = "\n\n".join(answer_parts)

            return ChatResponse(
                answer=answer_text,
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
                intent=intent_result.intent.value,
                tool_calls=executed_tools,
                ticket_id=ticket_id,
                lead_id=lead_id,
                escalated=False,
            )

        # 5. Path: Quotation Request or Sales Enquiry -> Create Lead
        if intent_result.intent in (CustomerIntent.QUOTATION_REQUEST, CustomerIntent.SALES_ENQUIRY):
            prod_interest = intent_result.detected_entities.get("product_category") or "NIEL Equipment"
            rating = intent_result.detected_entities.get("rating")
            if rating:
                prod_interest = f"{rating} {prod_interest}"

            lead_res = self.tool_dispatcher.execute_tool(
                "create_sales_lead",
                {
                    "product_interest": prod_interest,
                    "requirement_details": question,
                    "required_quantity": intent_result.detected_entities.get("quantity"),
                },
                session_id=session_id,
                customer_id=cid,
            )
            executed_tools.append({"tool": "create_sales_lead", "output": lead_res})
            lead_id = lead_res.get("lead_id")

            # Retrieve product technical info to assist customer
            rag_resp = self.rag_service.answer_question(
                question=question,
                top_k=top_k,
                conversation_history=effective_history,
                session_id=session_id,
            )
            executed_tools.append({"tool": "search_product_knowledge", "output": {"retrieved": len(rag_resp.citations)}})

            lead_notice = f"\n\n*(Sales Lead #{lead_id} logged. A NIEL commercial representative will review your request.)*"
            final_answer = rag_resp.answer + lead_notice

            return ChatResponse(
                answer=final_answer,
                citations=rag_resp.citations,
                pdf_attachments=rag_resp.pdf_attachments,
                evidence_sufficient=rag_resp.evidence_sufficient,
                clarification_needed=rag_resp.clarification_needed,
                request_id=request_id,
                usage=rag_resp.usage,
                intent=intent_result.intent.value,
                tool_calls=executed_tools,
                ticket_id=ticket_id,
                lead_id=lead_id,
                escalated=False,
            )

        # 6. Path: General Information & Greetings
        if intent_result.intent == CustomerIntent.GENERAL_INFORMATION:
            general_answer = (
                "Hello! Welcome to New India Electricals Ltd. (NIEL). We design, manufacture, and service "
                "high-efficiency industrial motors (IE2/IE3/IE4), power and distribution transformers, "
                "HT/LT switchgear panels, and industrial pumps. How can our engineering team assist your plant or project today?"
            )
            return ChatResponse(
                answer=general_answer,
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
                intent=intent_result.intent.value,
                tool_calls=executed_tools,
                ticket_id=ticket_id,
                lead_id=lead_id,
                escalated=False,
            )

        # 7. Default Product Knowledge / Technical Support / Recommendations Path
        # Use existing grounded RAG service for citations and strict evidence boundary
        rag_resp = self.rag_service.answer_question(
            question=question,
            top_k=top_k,
            conversation_history=effective_history,
            session_id=session_id,
        )
        executed_tools.append({
            "tool": "search_product_knowledge",
            "output": {"retrieved": len(rag_resp.citations)},
        })

        return ChatResponse(
            answer=rag_resp.answer,
            citations=rag_resp.citations,
            pdf_attachments=rag_resp.pdf_attachments,
            evidence_sufficient=rag_resp.evidence_sufficient,
            clarification_needed=rag_resp.clarification_needed,
            request_id=request_id,
            usage=rag_resp.usage,
            intent=intent_result.intent.value,
            tool_calls=executed_tools,
            ticket_id=ticket_id,
            lead_id=lead_id,
            escalated=False,
        )


_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Singleton accessor for AgentOrchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
