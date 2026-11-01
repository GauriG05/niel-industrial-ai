"""Intent classification service for NIEL Industrial AI Agent."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.app.schemas.intent import CustomerIntent, IntentClassificationResult
from backend.app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Hazardous electrical keywords that demand immediate safety escalation
HAZARD_KEYWORDS = [
    "smoke", "smoking", "fire", "spark", "sparking", "shock", "electric shock",
    "burning smell", "burned out", "burn", "explosion", "exploded", "flame", "blast"
]

# Explicit human escalation phrases
HUMAN_ESCALATION_PHRASES = [
    "talk to a human", "speak to a human", "talk to human", "human agent",
    "real person", "speak to representative", "connect to agent", "representative please",
    "talk to an engineer", "human support", "operator", "customer care agent"
]

# Quotation / RFQ patterns
QUOTATION_PATTERNS = [
    "quote", "quotation", "price quote", "pricing quote", "cost estimate", "rfq",
    "request for quotation", "commercial offer", "bulk pricing", "price list",
    "how much does it cost", "how much is"
]

# Sales enquiry patterns
SALES_PATTERNS = [
    "want to buy", "looking to purchase", "procure", "procurement", "dealer near",
    "distributor in", "sales enquiry", "sales inquiry", "order 5 units", "bulk order",
    "place an order"
]

# Complaint patterns
COMPLAINT_PATTERNS = [
    "complaint", "defective", "broken", "damaged", "failed within warranty",
    "bad quality", "stopped working", "faulty unit", "vibrating severely",
    "oil leaking", "dissatisfied", "escalate this issue", "file a claim"
]

# Technical support patterns
TECH_SUPPORT_PATTERNS = [
    "troubleshoot", "troubleshooting", "tripping", "breaker tripped", "overheating",
    "alarm", "error code", "maintenance", "wiring diagram", "terminal connection",
    "insulation resistance", "bearing lubrication", "winding temperature", "vibration",
    "not turning", "stalled", "abnormal noise"
]

# Recommendation patterns
RECOMMENDATION_PATTERNS = [
    "recommend", "suggest", "which motor", "which pump", "which transformer",
    "selection guide", "suitable for", "what should i choose", "best model for",
    "sizing recommendation"
]

# Order / delivery patterns
ORDER_DELIVERY_PATTERNS = [
    "lead time", "delivery time", "shipping timeline", "dispatch status",
    "transit time", "when will it arrive", "order status"
]


class IntentService:
    """Classifies user messages into the 9 core customer intents and extracts relevant entities."""

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        self.openai_service = openai_service or OpenAIService()

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract domain entities such as product category, power/capacity, and urgency."""
        entities: Dict[str, Any] = {}
        lower = text.lower()

        # Product category detection
        categories = []
        if re.search(r"\b(motor|motors|induction motor|flameproof|squirrel cage)\b", lower):
            categories.append("Motors")
        if re.search(r"\b(pump|pumps|submersible|centrifugal|end suction)\b", lower):
            categories.append("Pumps")
        if re.search(r"\b(transformer|transformers|distribution transformer|dry type|oil cooled)\b", lower):
            categories.append("Transformers")
        if re.search(r"\b(switchgear|mcc|pcc|panel|vfd panel|breaker|switchboard)\b", lower):
            categories.append("Switchgear Panels")
        if categories:
            entities["product_category"] = categories[0]
            entities["all_detected_categories"] = categories

        # Power / Rating extraction (e.g. "75kW", "100 HP", "2000 kVA", "11kV")
        rating_match = re.search(r"(\d+(\.\d+)?)\s*(kw|hp|kva|mva|kv|v|rpm|bar|m3/hr|amps?)\b", lower, re.IGNORECASE)
        if rating_match:
            entities["rating"] = rating_match.group(0).upper()

        # Quantity extraction (e.g. "5 units", "10 pieces", "2 nos")
        qty_match = re.search(r"(\d+)\s*(units?|pieces?|nos?|sets?)\b", lower, re.IGNORECASE)
        if qty_match:
            entities["quantity"] = int(qty_match.group(1))

        # Check for safety hazard
        is_hazard = any(hk in lower for hk in HAZARD_KEYWORDS)
        if is_hazard:
            entities["urgency"] = "CRITICAL"
            entities["safety_hazard_detected"] = True
        else:
            entities["urgency"] = "MEDIUM"

        return entities

    def classify_rule_based(self, text: str) -> IntentClassificationResult:
        """Deterministic heuristic classifier with entity extraction and safety checks."""
        lower = text.lower()
        entities = self.extract_entities(text)

        # 1. Safety Hazard Check -> escalate immediately to human engineering support
        if entities.get("safety_hazard_detected"):
            return IntentClassificationResult(
                intent=CustomerIntent.TECHNICAL_SUPPORT,
                confidence=0.98,
                detected_entities=entities,
                requires_escalation=True,
                suggested_action="escalate_to_human",
                reasoning="Safety hazard detected (smoke, fire, sparking, or electrical shock hazard).",
            )

        # 2. Explicit Human Request
        human_trigger = (
            any(phrase in lower for phrase in HUMAN_ESCALATION_PHRASES) or
            bool(re.search(r"\b(talk|speak|connect|transfer)\b.*?\b(human|person|representative|agent|engineer|operator)\b", lower))
        )
        if human_trigger:
            return IntentClassificationResult(
                intent=CustomerIntent.HUMAN_SUPPORT_REQUEST,
                confidence=0.99,
                detected_entities=entities,
                requires_escalation=True,
                suggested_action="escalate_to_human",
                reasoning="Visitor explicitly requested human representative assistance.",
            )

        # 3. Quotation Request
        if any(pat in lower for pat in QUOTATION_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.QUOTATION_REQUEST,
                confidence=0.92,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="create_sales_lead",
                reasoning="Customer requested quotation or pricing information.",
            )

        # 4. Complaints / Breakdowns
        if any(pat in lower for pat in COMPLAINT_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.COMPLAINT,
                confidence=0.90,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="create_support_ticket",
                reasoning="Customer reported defect, breakdown, or issue requiring ticket creation.",
            )

        # 5. Technical Support / Troubleshooting
        if any(pat in lower for pat in TECH_SUPPORT_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.TECHNICAL_SUPPORT,
                confidence=0.88,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="search_product_knowledge",
                reasoning="Technical troubleshooting or specification support request.",
            )

        # 6. Product Recommendation
        if any(pat in lower for pat in RECOMMENDATION_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.PRODUCT_RECOMMENDATION,
                confidence=0.86,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="search_product_knowledge",
                reasoning="Customer requested guidance on selecting appropriate equipment.",
            )

        # 7. Sales Enquiry / Purchase
        if any(pat in lower for pat in SALES_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.SALES_ENQUIRY,
                confidence=0.85,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="create_sales_lead",
                reasoning="Purchase intent or distributor inquiry detected.",
            )

        # 8. Order / Delivery Enquiry
        if any(pat in lower for pat in ORDER_DELIVERY_PATTERNS):
            return IntentClassificationResult(
                intent=CustomerIntent.ORDER_DELIVERY_ENQUIRY,
                confidence=0.85,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="search_product_knowledge",
                reasoning="Order fulfillment or shipping inquiry.",
            )

        # 9. General Information vs Product Enquiry Default
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "thank", "who are you"]
        if any(re.search(rf"\b{g}\b", lower) for g in greetings) and not entities.get("product_category"):
            return IntentClassificationResult(
                intent=CustomerIntent.GENERAL_INFORMATION,
                confidence=0.80,
                detected_entities=entities,
                requires_escalation=False,
                suggested_action="direct_response",
                reasoning="General greeting or organizational information.",
            )

        # Default to Product Enquiry with search_product_knowledge
        return IntentClassificationResult(
            intent=CustomerIntent.PRODUCT_ENQUIRY,
            confidence=0.75,
            detected_entities=entities,
            requires_escalation=False,
            suggested_action="search_product_knowledge",
            reasoning="Customer inquiring about product specifications or capabilities.",
        )

    def classify_intent(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> IntentClassificationResult:
        """
        Classify intent using heuristic checks and LLM when live credentials are configured,
        with automatic fallback to deterministic rule engine.
        """
        # Safety hazards & explicit human handoff always trigger immediate rule-based action
        heuristic_res = self.classify_rule_based(text)
        if heuristic_res.requires_escalation:
            return heuristic_res

        # If live OpenAI is configured, use structured LLM classification for nuanced queries
        if self.openai_service.is_live_configured:
            try:
                client = self.openai_service._get_client()
                system_prompt = (
                    "You are an industrial customer support intent classifier for New India Electricals Ltd (NIEL).\n"
                    "Classify the customer's query into one of the following exact intents:\n"
                    "PRODUCT_ENQUIRY, TECHNICAL_SUPPORT, PRODUCT_RECOMMENDATION, QUOTATION_REQUEST, "
                    "SALES_ENQUIRY, COMPLAINT, ORDER_DELIVERY_ENQUIRY, GENERAL_INFORMATION, HUMAN_SUPPORT_REQUEST.\n"
                    "Return ONLY valid JSON matching this schema:\n"
                    "{\n"
                    '  "intent": "<EXACT_INTENT>",\n'
                    '  "confidence": 0.0 to 1.0,\n'
                    '  "requires_escalation": boolean,\n'
                    '  "suggested_action": "search_product_knowledge" | "create_support_ticket" | "create_sales_lead" | "escalate_to_human" | "direct_response",\n'
                    '  "reasoning": "brief explanation"\n'
                    "}"
                )

                messages = [{"role": "system", "content": system_prompt}]
                if conversation_history:
                    for turn in conversation_history[-3:]:
                        messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
                messages.append({"role": "user", "content": text})

                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                raw_json = completion.choices[0].message.content or "{}"
                data = json.loads(raw_json)

                matched_intent = CustomerIntent(data.get("intent", heuristic_res.intent.value))
                entities = self.extract_entities(text)
                return IntentClassificationResult(
                    intent=matched_intent,
                    confidence=float(data.get("confidence", 0.9)),
                    detected_entities=entities,
                    requires_escalation=bool(data.get("requires_escalation", False)),
                    suggested_action=data.get("suggested_action", heuristic_res.suggested_action),
                    reasoning=data.get("reasoning", "Classified via LLM"),
                )
            except Exception as exc:
                logger.warning("LLM intent classification failed (%s); using heuristic fallback", exc)

        return heuristic_res


_intent_service_instance: Optional[IntentService] = None


def get_intent_service() -> IntentService:
    """Singleton accessor for IntentService."""
    global _intent_service_instance
    if _intent_service_instance is None:
        _intent_service_instance = IntentService()
    return _intent_service_instance
