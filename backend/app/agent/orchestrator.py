"""Agent Orchestrator: manages customer intent, multi-turn context, tool execution, and grounded replies."""

import json
import logging
import re
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
        """
        Securely resolve active customer ID. Never blindly trust client-supplied customer_id.
        Enforces session binding to prevent customer impersonation across sessions.
        """
        if not session_id:
            # Without session tracking, no verified customer identity can be established
            return None

        # Check DB session binding
        bound_cid = self.session_service.get_session_customer_id(session_id)
        if bound_cid:
            if customer_id and customer_id != bound_cid:
                logger.warning(
                    "SECURITY: Customer ID mismatch in session %s. Client passed '%s', but session is bound to '%s'. Enforcing bound customer.",
                    session_id, customer_id, bound_cid
                )
            return bound_cid

        # If session is not yet bound but client supplies a customer_id, verify existence before binding
        if customer_id:
            customer_exists = self.customer_service.get_customer_context(customer_id) is not None
            if customer_exists:
                self.session_service.link_customer_to_session(session_id, customer_id)
                return customer_id
            else:
                logger.warning("SECURITY: Untrusted non-existent customer_id '%s' rejected for session %s", customer_id, session_id)
                return None

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
            logger.warning("KILL SWITCH ACTIVE: AI processing completely disabled. Returning human support fallback.")
            from urllib.parse import quote
            wa_text = "Hello NIEL Team, I would like direct human support assistance regarding an inquiry on your website."
            wa_url = f"https://wa.me/919741307999?text={quote(wa_text)}"
            return ChatResponse(
                answer=(
                    "The automated AI assistant is temporarily paused for scheduled engineering maintenance. "
                    "Our human engineering and sales support team is standing by to assist you directly.\n\n"
                    f"{wa_url}\n\n"
                    "You can also reach our main office directly at sales@newindiaelectricals.com or call +91 80 42434343."
                ),
                citations=[],
                pdf_attachments=[],
                site_url="https://newindiaelectricals.com",
                whatsapp_url=wa_url,
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
                intent="KILL_SWITCH_FALLBACK",
                tool_calls=[],
                escalated=True,
            )

        from backend.app.agent.guardrails import detect_prompt_injection, sanitize_untrusted_text

        is_injection, injection_reason = detect_prompt_injection(question)
        if is_injection:
            logger.warning("SECURITY: Prompt injection attempt blocked for session %s: %s", session_id, injection_reason)
            from urllib.parse import quote
            wa_text = "Hello NIEL Team, I would like assistance regarding an inquiry on your website."
            wa_url = f"https://wa.me/919741307999?text={quote(wa_text)}"
            return ChatResponse(
                answer=(
                    "I am the NIEL Industrial Intelligence Assistant, dedicated strictly to providing verified specifications "
                    "and engineering documentation for New India Electricals Ltd. equipment (motors, transformers, "
                    "pumps, switchgear). I cannot alter system instructions, execute arbitrary commands, or disclose "
                    "internal prompts. How can I assist with your industrial equipment needs today?"
                ),
                citations=[],
                pdf_attachments=[],
                site_url="https://newindiaelectricals.com",
                whatsapp_url=wa_url,
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
                intent="SECURITY_DEFENSE_TRIGGERED",
                tool_calls=[],
                escalated=False,
            )

        clean_question = sanitize_untrusted_text(question)

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

            # Build context summary from entities and conversation history
            context_product = intent_result.detected_entities.get("product_category", "")
            rating = intent_result.detected_entities.get("rating", "")
            context_spec = f"{rating} {context_product}".strip() if rating and context_product else (context_product or rating)

            if not context_spec and effective_history:
                for turn in reversed(effective_history):
                    role = turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", "")
                    content = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", "")
                    if role == "user":
                        c_clean = content.strip()
                        if len(c_clean) > 3 and not re.search(r"\b(connect|human|agent|person|representative|sales)\b", c_clean, re.IGNORECASE):
                            context_spec = c_clean[:100]
                            break

            is_sales = bool(re.search(r"\b(sales|quote|pricing|commercial|buy|purchase)\b", question, re.IGNORECASE))

            if is_sales:
                lead_res = self.tool_dispatcher.execute_tool(
                    "create_sales_lead",
                    {
                        "product_interest": context_spec or "NIEL Equipment",
                        "requirement_details": question,
                    },
                    session_id=session_id,
                    customer_id=cid,
                )
                executed_tools.append({"tool": "create_sales_lead", "output": lead_res})
                lead_id = lead_res.get("lead_id")

            # Compose tailored WhatsApp pre-filled text
            from urllib.parse import quote
            if context_spec:
                wa_summary = f"Hello NIEL Team, I would like to connect with a representative regarding {context_spec}."
            elif is_sales:
                wa_summary = "Hello NIEL Team, I would like to speak with your sales engineering team regarding product inquiries."
            else:
                wa_summary = "Hello NIEL Team, I would like human support assistance regarding an inquiry on your website."

            wa_url = f"https://wa.me/919741307999?text={quote(wa_summary)}"

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
                    "this session immediately.\n\n"
                    f"Immediate emergency escalation on WhatsApp (+91 97413 07999):\n{wa_url}"
                )
            else:
                if context_spec:
                    team_name = "Sales & Commercial Engineering Team" if is_sales else "Support & Engineering Team"
                    answer_text = (
                        f"Connecting you with the NIEL {team_name} on WhatsApp (+91 97413 07999) regarding **{context_spec}**.\n\n"
                        f"{wa_url}\n\n"
                        "Click the WhatsApp button to connect directly with our engineers. You can also continue asking any technical questions right here!"
                    )
                elif is_sales:
                    answer_text = (
                        "Connecting you with the NIEL Sales & Commercial Engineering Team on WhatsApp (+91 97413 07999).\n\n"
                        f"{wa_url}\n\n"
                        "Click the WhatsApp button to connect directly with our sales engineers for pricing, lead times, and quotations. You can also continue asking right here!"
                    )
                else:
                    answer_text = (
                        "Connecting you to NIEL Support on WhatsApp (+91 97413 07999).\n\n"
                        f"{wa_url}\n\n"
                        "Click the WhatsApp button to connect directly with an engineering representative. You can also continue asking any technical questions right here!"
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
                whatsapp_url=wa_url,
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
                site_url=rag_resp.site_url,
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
            site_url=rag_resp.site_url,
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
