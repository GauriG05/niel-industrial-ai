"""Tests for IntentService: intent classification, entity extraction, and safety guardrails."""

import pytest
from backend.app.schemas.intent import CustomerIntent
from backend.app.services.intent_service import IntentService


@pytest.fixture
def intent_service():
    return IntentService()


def test_safety_hazard_triggers_immediate_escalation(intent_service):
    """Verify that electrical hazards (smoke, sparks, shocks) trigger safety escalation."""
    queries = [
        "The 75kW motor has smoke coming out of the junction box!",
        "There is severe sparking and a burning smell from the main breaker panel.",
        "An operator received an electric shock from the transformer casing.",
    ]
    for q in queries:
        res = intent_service.classify_intent(q)
        assert res.requires_escalation is True
        assert res.suggested_action == "escalate_to_human"
        assert res.detected_entities.get("urgency") == "CRITICAL"


def test_explicit_human_request(intent_service):
    """Verify that requests for a human representative trigger HUMAN_SUPPORT_REQUEST."""
    queries = [
        "Can I speak to a human representative please?",
        "I need to talk to an engineer right now.",
        "Connect me to an agent.",
    ]
    for q in queries:
        res = intent_service.classify_intent(q)
        assert res.intent == CustomerIntent.HUMAN_SUPPORT_REQUEST
        assert res.requires_escalation is True
        assert res.suggested_action == "escalate_to_human"


def test_quotation_request(intent_service):
    """Verify quotation and RFQ inquiries map to QUOTATION_REQUEST."""
    query = "Please send me a price quote for 5 units of 45kW IE3 motors."
    res = intent_service.classify_intent(query)
    assert res.intent == CustomerIntent.QUOTATION_REQUEST
    assert res.suggested_action == "create_sales_lead"
    assert res.detected_entities.get("product_category") == "Motors"
    assert res.detected_entities.get("quantity") == 5
    assert res.detected_entities.get("rating") == "45KW"


def test_complaint_and_defect(intent_service):
    """Verify breakdown and defective equipment reports map to COMPLAINT."""
    query = "Our 2000kVA transformer has a broken drain valve and is leaking oil severely."
    res = intent_service.classify_intent(query)
    assert res.intent == CustomerIntent.COMPLAINT
    assert res.suggested_action == "create_support_ticket"
    assert res.detected_entities.get("product_category") == "Transformers"
    assert res.detected_entities.get("rating") == "2000KVA"


def test_product_recommendation(intent_service):
    """Verify equipment sizing and selection queries map to PRODUCT_RECOMMENDATION."""
    query = "Which pump model do you recommend for pumping raw effluent with solids?"
    res = intent_service.classify_intent(query)
    assert res.intent == CustomerIntent.PRODUCT_RECOMMENDATION
    assert res.suggested_action == "search_product_knowledge"
    assert res.detected_entities.get("product_category") == "Pumps"


def test_entity_extraction_categories(intent_service):
    """Verify multi-category and entity detection accuracy."""
    res_motor = intent_service.extract_entities("We need squirrel cage induction motors 315kW.")
    assert res_motor["product_category"] == "Motors"
    assert res_motor["rating"] == "315KW"

    res_switchgear = intent_service.extract_entities("What are the ratings of the MCC panel switchgear?")
    assert res_switchgear["product_category"] == "Switchgear Panels"

