"""Agent tool definitions, schemas, and execution dispatcher."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from backend.app.services.customer_service import get_customer_service
from backend.app.services.lead_service import get_lead_service
from backend.app.services.rag_service import get_rag_service
from backend.app.services.session_service import get_session_service
from backend.app.services.ticket_service import get_ticket_service

logger = logging.getLogger(__name__)

# Official OpenAI tool schemas for the 7 agent tools
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
            "description": "Create a formal support ticket for post-sales faults, maintenance requests, warranty claims, or troubleshooting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_category": {
                        "type": "string",
                        "description": "Equipment category: 'Motors', 'Pumps', 'Transformers', or 'Switchgear Panels'.",
                    },
                    "issue_description": {
                        "type": "string",
                        "description": "Detailed description of the fault, alarm, or maintenance issue.",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                        "description": "Assessed issue severity.",
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
            "description": "Record a high-intent B2B sales lead or quotation request for NIEL commercial engineers to follow up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_interest": {
                        "type": "string",
                        "description": "Specific product or rating requested (e.g. '75kW IE3 Motor' or '2000kVA Transformer').",
                    },
                    "requirement_details": {
                        "type": "string",
                        "description": "Specifications, operating environment, and application details.",
                    },
                    "required_quantity": {
                        "type": "integer",
                        "description": "Number of units required.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Delivery destination or project site location.",
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
            "description": "Escalate the session to an active human support engineer or sales manager immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for human takeover (e.g. safety hazard, customer requested representative, out-of-scope question).",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


class ToolDispatcher:
    """Executes agent tools with error isolation, input validation, and audit recording."""

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
        """Dispatch tool call by name with robust exception safety."""
        logger.info("Executing tool '%s' with args %s (session=%s, customer=%s)", name, arguments, session_id, customer_id)

        try:
            if name == "search_product_knowledge":
                query = arguments.get("query", "")
                top_k = int(arguments.get("top_k", 4))
                category = arguments.get("category")
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
                target_cid = arguments.get("customer_id") or customer_id
                if not target_cid:
                    return {"status": "error", "message": "No customer ID provided"}
                ctx = self.customer_service.get_customer_context(target_cid)
                if not ctx:
                    return {"status": "not_found", "message": f"Customer '{target_cid}' not found"}
                return {"status": "success", "profile": ctx}

            elif name == "get_customer_history":
                target_cid = arguments.get("customer_id") or customer_id
                if not target_cid:
                    return {"status": "error", "message": "No customer ID provided"}
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
                email = arguments.get("email")
                phone = arguments.get("phone")
                name_val = arguments.get("name")
                company = arguments.get("company")

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
                    industry=arguments.get("industry"),
                    interests=arguments.get("interests"),
                    preferences=arguments.get("preferences"),
                )
                self.customer_service.record_consent(cust.id)
                return {
                    "status": "success",
                    "customer_id": cust.id,
                    "message": "Customer information successfully updated with consent.",
                }

            elif name == "create_support_ticket":
                category = arguments.get("product_category", "General")
                desc = arguments.get("issue_description", "")
                sev = arguments.get("severity")
                ticket, advisory = self.ticket_service.create_ticket(
                    product_category=category,
                    issue_description=desc,
                    customer_id=customer_id,
                    session_id=session_id,
                    severity_override=sev,
                )
                res: Dict[str, Any] = {
                    "status": "success",
                    "ticket_id": ticket.id,
                    "product_category": ticket.product_category,
                    "severity": ticket.severity,
                    "ticket_status": ticket.status,
                }
                if advisory:
                    res["safety_advisory"] = advisory
                return res

            elif name == "create_sales_lead":
                lead = self.lead_service.create_lead(
                    product_interest=arguments.get("product_interest", ""),
                    customer_id=customer_id,
                    session_id=session_id,
                    requirement_details=arguments.get("requirement_details"),
                    required_quantity=arguments.get("required_quantity"),
                    location=arguments.get("location"),
                )
                return {
                    "status": "success",
                    "lead_id": lead.id,
                    "priority": lead.priority,
                    "lead_status": lead.status,
                    "message": "Sales lead registered for commercial engineering review.",
                }

            elif name == "escalate_to_human":
                reason = arguments.get("reason", "Customer requested escalation")
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
