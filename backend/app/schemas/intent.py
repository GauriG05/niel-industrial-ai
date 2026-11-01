"""Schemas for customer intent classification and entity extraction."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CustomerIntent(str, Enum):
    """The 9 primary customer intents supported by NIEL Industrial AI Agent."""
    PRODUCT_ENQUIRY = "PRODUCT_ENQUIRY"                      # Specs, ratings, models, dimensions
    TECHNICAL_SUPPORT = "TECHNICAL_SUPPORT"                  # Troubleshooting, alarms, maintenance, wiring
    PRODUCT_RECOMMENDATION = "PRODUCT_RECOMMENDATION"        # Selecting motor/pump for an application
    QUOTATION_REQUEST = "QUOTATION_REQUEST"                  # RFQ, bulk pricing, estimates, commercial proposal
    SALES_ENQUIRY = "SALES_ENQUIRY"                          # Lead capture, purchase enquiry, distributor contact
    COMPLAINT = "COMPLAINT"                                  # Defect, breakdown, warranty claim, delayed response
    ORDER_DELIVERY_ENQUIRY = "ORDER_DELIVERY_ENQUIRY"        # Lead times, dispatch status, shipping terms
    GENERAL_INFORMATION = "GENERAL_INFORMATION"              # About NIEL, certifications, plant location, greetings
    HUMAN_SUPPORT_REQUEST = "HUMAN_SUPPORT_REQUEST"          # Explicit request to talk with a representative or agent


class IntentClassificationResult(BaseModel):
    """Structured result returned by the intent classification engine."""
    intent: CustomerIntent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    detected_entities: Dict[str, Any] = Field(default_factory=dict)
    requires_escalation: bool = False
    suggested_action: str = "search_product_knowledge"
    reasoning: Optional[str] = None

