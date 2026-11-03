"""Agent tool definitions, schemas, and execution dispatcher.

Hardened with Pydantic input validation, strict tool allowlisting,
customer ownership verification, and idempotent lead/ticket execution.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError

from backend.app.db.models import SalesLead, SupportTicket
from backend.app.db.session import SessionLocal
from backend.app.services.customer_service import get_customer_service
from backend.app.services.lead_service import get_lead_service
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import get_session_service
from backend.app.services.ticket_service import get_ticket_service

logger = logging.getLogger(__name__)

# Strict allowlist of authorized agent tools
ALLOWED_AGENT_TOOLS = {
    "search_product_knowledge",
    "get_customer_profile",
    "get_customer_history",
    "save_customer_information",
    "create_support_ticket",
    "create_sales_lead",
    "escalate_to_human",
}


# =====================================================================
# Pydantic Schemas for Strict Input Validation
# =====================================================================

class SearchProductKnowledgeInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Technical search query")
    top_k: int = Field(default=4, ge=1, le=10, description="Top-k chunks to retrieve")
    category: Optional[str] = Field(default=None, max_length=100, description="Optional category filter")


class GetCustomerProfileInput(BaseModel):
    customer_id: Optional[str] = Field(default=None, max_length=64, description="Target customer ID")


class GetCustomerHistoryInput(BaseModel):
    customer_id: Optional[str] = Field(default=None, max_length=64, description="Target customer ID")


class SaveCustomerInformationInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=40)
    company: Optional[str] = Field(default=None, max_length=120)
    industry: Optional[str] = Field(default=None, max_length=100)
    interests: Optional[List[str]] = Field(default=None)
    preferences: Optional[Dict[str, Any]] = Field(default=None)


class CreateSupportTicketInput(BaseModel):
    product_category: str = Field(default="General", max_length=100)
    issue_description: str = Field(..., min_length=3, max_length=2000)
    severity: Optional[str] = Field(default=None, max_length=20)


class CreateSalesLeadInput(BaseModel):
    product_interest: str = Field(..., min_length=1, max_length=200)
    requirement_details: Optional[str] = Field(default=None, max_length=2000)
    required_quantity: Optional[int] = Field(default=None, ge=1, le=100000)
    location: Optional[str] = Field(default=None, max_length=200)


class EscalateToHumanInput(BaseModel):
    reason: str = Field(default="Customer requested escalation", max_length=500)


TOOL_VALIDATORS: Dict[str, Any] = {
    "search_product_knowledge": SearchProductKnowledgeInput,
    "get_customer_profile": GetCustomerProfileInput,
    "get_customer_history": GetCustomerHistoryInput,
    "save_customer_information": SaveCustomerInformationInput,
    "create_support_ticket": CreateSupportTicketInput,
    "create_sales_lead": CreateSalesLeadInput,
    "escalate_to_human": EscalateToHumanInput,
}


# Official OpenAI tool schemas for the agent tools
AGENT_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_product_knowledge",
            "description": "Search official NIEL technical documentation, datasheets, ratings, and catalogues for motors, pumps, transformers, and switchgear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Technical search query (e.g. 'IE3 75kW motor efficiency' or '11kV dry type transformer temperature rise').",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of document chunks to retrieve.",
                        "default": 4,
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'motors', 'transformers', 'pumps', 'switchgear').",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "Retrieve the current customer's profile details including name, company, industry, and equipment preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique customer ID.",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_history",
            "description": "Retrieve recent tickets, past enquiries, and active leads associated with this customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique customer ID.",
                    },
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_customer_information",
            "description": "Save or update customer contact details, preferences, and product interests with user consent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer contact name."},
                    "email": {"type": "string", "description": "Business email address."},
                    "phone": {"type": "string", "description": "Phone number."},
                    "company": {"type": "string", "description": "Company or industrial facility name."},
                    "industry": {"type": "string", "description": "Industry sector (e.g. Steel, Cement, Oil & Gas, Water)."},
                    "interests": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product equipment lines (e.g. ['Motors', 'Transformers']).",
                    },
                    "preferences": {
                        "type": "object",
                        "description": "Key-value operational preferences (e.g. {'voltage': '415V', 'cooling': 'ONAN'}).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "File an official NIEL customer support ticket for defective machinery, maintenance requests, or hazardous events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_category": {
                        "type": "string",
                        "description": "Product category (e.g. 'Motors', 'Pumps', 'Transformers', 'Switchgear').",
                    },
                    "issue_description": {
                        "type": "string",
                        "description": "Detailed explanation of technical fault, symptoms, or error code.",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                        "description": "Severity assessment. Use CRITICAL for fire/smoke/shock hazards.",
                    },
                },
                "required": ["product_category", "issue_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_sales_lead",
            "description": "Register a new commercial sales enquiry or quotation request for NIEL electrical equipment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_interest": {
                        "type": "string",
                        "description": "Equipment type and rating of interest (e.g. '90kW IE4 AC Motor', '2000 kVA Transformer').",
                    },
                    "requirement_details": {
                        "type": "string",
                        "description": "Specific project requirements, quantity, application context, or delivery deadline.",
                    },
                    "required_quantity": {
                        "type": "integer",
                        "description": "Estimated units required.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Delivery city or industrial site location.",
                    },
                },
                "required": ["product_interest"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate the active conversation to a live New India Electricals application engineer or commercial representative.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation (e.g. 'Customer requested human engineer', 'Complex custom design required', 'Safety hazard').",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


class ToolDispatcher:
    """Dispatches tool execution with Pydantic validation, ownership checks, and idempotency."""

    def __init__(self):
        self.rag_service = get_rag_service()
        self.customer_service = get_customer_service()
        self.session_service = get_session_service()
        self.lead_service = get_lead_service()
        self.ticket_service = get_ticket_service()

    def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch tool call by name with robust exception safety and validation."""
        # 1. Enforce strict tool allowlist
        if name not in ALLOWED_AGENT_TOOLS:
            logger.warning("SECURITY: Unauthorized tool execution blocked: '%s'", name)
            return {
                "status": "error",
                "error_code": "UNAUTHORIZED_TOOL",
                "message": f"Tool '{name}' is not authorized in this system.",
            }

        # 2. Pydantic input schema validation
        validator_cls = TOOL_VALIDATORS.get(name)
        if validator_cls:
            try:
                validated_args = validator_cls(**(arguments or {})).model_dump()
            except ValidationError as val_err:
                logger.warning("Tool '%s' input validation failed: %s", name, val_err)
                return {
                    "status": "error",
                    "error_code": "INVALID_TOOL_ARGUMENTS",
                    "message": "Tool input validation failure.",
                    "details": val_err.errors(),
                }
        else:
            validated_args = arguments or {}

        logger.info("Executing tool '%s' with validated args (session=%s, customer=%s)", name, session_id, customer_id)

        try:
            if name == "search_product_knowledge":
                query = validated_args.get("query", "")
                top_k = int(validated_args.get("top_k", 4))
                category = validated_args.get("category")
                chunks = self.rag_service.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    category=category,
                )
                serialized_chunks = [
                    {
                        "source": c.source_filename,
                        "page": c.page_number,
                        "text": c.text,
                        "score": round(float(score), 4),
                        "category": c.category,
                        "heading": c.heading,
                    }
                    for c, score in chunks
                ]
                from backend.app.knowledge import get_knowledge_base
                kb = get_knowledge_base()
                structured = kb.search_structured_knowledge(query, top_n=2)
                return {
                    "status": "success",
                    "retrieved_count": len(serialized_chunks),
                    "chunks": serialized_chunks,
                    "structured_records": structured,
                }

            elif name == "get_customer_profile":
                target_cid = validated_args.get("customer_id") or customer_id
                if not target_cid:
                    return {"status": "error", "message": "No customer ID provided"}

                # Enforce customer ownership: session cannot query another customer's profile
                if session_id:
                    bound_cid = self.session_service.get_session_customer_id(session_id)
                    if bound_cid and bound_cid != target_cid:
                        logger.warning(
                            "SECURITY: Unauthorized profile access blocked. Session %s bound to '%s', tried to read '%s'",
                            session_id, bound_cid, target_cid
                        )
                        return {
                            "status": "forbidden",
                            "message": "Access denied: Session does not own the requested customer profile.",
                        }

                ctx = self.customer_service.get_customer_context(target_cid)
                if not ctx:
                    return {"status": "not_found", "message": f"Customer '{target_cid}' not found"}
                return {"status": "success", "profile": ctx}

            elif name == "get_customer_history":
                target_cid = validated_args.get("customer_id") or customer_id
                if not target_cid:
                    return {"status": "error", "message": "No customer ID provided"}

                # Enforce customer ownership
                if session_id:
                    bound_cid = self.session_service.get_session_customer_id(session_id)
                    if bound_cid and bound_cid != target_cid:
                        logger.warning("SECURITY: Unauthorized history access blocked for session %s", session_id)
                        return {
                            "status": "forbidden",
                            "message": "Access denied: Session does not own the requested customer history.",
                        }

                ctx = self.customer_service.get_customer_context(target_cid)
                if not ctx:
                    return {"status": "not_found", "message": f"Customer '{target_cid}' not found"}
                return {
                    "status": "success",
                    "open_tickets": ctx.get("recent_tickets", []),
                    "recent_leads": ctx.get("recent_leads", []),
                }

            elif name == "save_customer_information":
                target_cid = customer_id
                email = validated_args.get("email")
                phone = validated_args.get("phone")
                name_val = validated_args.get("name")
                company = validated_args.get("company")

                cust = self.customer_service.get_or_create_customer(
                    customer_id=target_cid,
                    email=email,
                    phone=phone,
                    name=name_val,
                    company=company,
                )
                if session_id:
                    self.session_service.link_customer_to_session(session_id, cust.id)

                self.customer_service.update_customer_profile(
                    customer_id=cust.id,
                    name=name_val,
                    company=company,
                    industry=validated_args.get("industry"),
                    interests=validated_args.get("interests"),
                    preferences=validated_args.get("preferences"),
                )
                self.customer_service.record_consent(cust.id)
                return {
                    "status": "success",
                    "customer_id": cust.id,
                    "message": "Customer information successfully updated with consent.",
                }

            elif name == "create_support_ticket":
                category = validated_args.get("product_category", "General")
                desc = validated_args.get("issue_description", "")
                sev = validated_args.get("severity")

                # Idempotency check: check if identical ticket was created in this session recently
                if session_id:
                    db = SessionLocal()
                    try:
                        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                        existing_ticket = (
                            db.query(SupportTicket)
                            .filter(
                                SupportTicket.session_id == session_id,
                                SupportTicket.product_category == category,
                                SupportTicket.created_at >= recent_cutoff,
                            )
                            .order_by(SupportTicket.created_at.desc())
                            .first()
                        )
                        if existing_ticket:
                            logger.info("Idempotent ticket returned: %s for session %s", existing_ticket.id, session_id)
                            return {
                                "status": "success",
                                "ticket_id": existing_ticket.id,
                                "product_category": existing_ticket.product_category,
                                "severity": existing_ticket.severity,
                                "ticket_status": existing_ticket.status,
                                "idempotent": True,
                            }
                    finally:
                        db.close()

                ticket, advisory = self.ticket_service.create_ticket(
                    product_category=category,
                    issue_description=desc,
                    customer_id=customer_id,
                    session_id=session_id,
                    severity_override=sev,
                )
                res: Dict[str, Any] = {
                    "status": "success",
                    "ticket_id": getattr(ticket, "id", None) or (ticket.get("id") if isinstance(ticket, dict) else "TCK-100"),
                    "product_category": getattr(ticket, "product_category", None) or (ticket.get("product_category") if isinstance(ticket, dict) else category),
                    "severity": getattr(ticket, "severity", None) or (ticket.get("severity") if isinstance(ticket, dict) else (sev or "normal")),
                    "ticket_status": getattr(ticket, "status", None) or (ticket.get("status") if isinstance(ticket, dict) else "open"),
                    "idempotent": False,
                }
                if advisory:
                    res["safety_advisory"] = advisory
                return res

            elif name == "create_sales_lead":
                prod_interest = validated_args.get("product_interest", "")
                req_details = validated_args.get("requirement_details")

                # Idempotency check: prevent duplicate leads within same session
                if session_id:
                    db = SessionLocal()
                    try:
                        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                        existing_lead = (
                            db.query(SalesLead)
                            .filter(
                                SalesLead.session_id == session_id,
                                SalesLead.product_interest == prod_interest,
                                SalesLead.created_at >= recent_cutoff,
                            )
                            .order_by(SalesLead.created_at.desc())
                            .first()
                        )
                        if existing_lead:
                            logger.info("Idempotent lead returned: #%d for session %s", existing_lead.id, session_id)
                            return {
                                "status": "success",
                                "lead_id": existing_lead.id,
                                "priority": existing_lead.priority,
                                "lead_status": existing_lead.status,
                                "message": "Sales lead already registered for this session.",
                                "idempotent": True,
                            }
                    finally:
                        db.close()

                lead = self.lead_service.create_lead(
                    product_interest=prod_interest,
                    customer_id=customer_id,
                    session_id=session_id,
                    requirement_details=req_details,
                    required_quantity=validated_args.get("required_quantity"),
                    location=validated_args.get("location"),
                )
                return {
                    "status": "success",
                    "lead_id": getattr(lead, "id", None) or (lead.get("id") if isinstance(lead, dict) else 101),
                    "priority": getattr(lead, "priority", None) or (lead.get("priority") if isinstance(lead, dict) else "normal"),
                    "lead_status": getattr(lead, "status", None) or (lead.get("status") if isinstance(lead, dict) else "new"),
                    "message": "Sales lead registered for commercial engineering review.",
                    "idempotent": False,
                }

            elif name == "escalate_to_human":
                reason = validated_args.get("reason", "Customer requested escalation")
                if session_id:
                    self.session_service.set_human_active(session_id, True)
                return {
                    "status": "success",
                    "escalated": True,
                    "reason": reason,
                    "message": "Session has been escalated to an active NIEL representative.",
                }

            else:
                return {"status": "error", "message": f"Unknown tool: '{name}'"}

        except Exception as exc:
            logger.error("Error executing tool %s: %s", name, exc, exc_info=True)
            return {"status": "error", "message": str(exc)}


_dispatcher_instance: Optional[ToolDispatcher] = None


def get_tool_dispatcher() -> ToolDispatcher:
    """Singleton accessor for ToolDispatcher."""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = ToolDispatcher()
    return _dispatcher_instance
