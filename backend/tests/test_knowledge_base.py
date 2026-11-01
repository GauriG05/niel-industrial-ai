"""Unit and integration tests for the NIEL Structured Knowledge Base and RAG integration."""

import pytest
from fastapi.testclient import TestClient

from backend.app.knowledge import get_knowledge_base, NIELKnowledgeBase
from backend.app.main import app
from backend.app.schemas.chat import ChatTurn
from backend.app.services.rag_service import get_rag_service
from backend.app.agent.tools import get_tool_dispatcher

client = TestClient(app)


def test_knowledge_base_all_12_categories_present():
    """Verify that all 12 required knowledge categories are loaded in the registry."""
    kb = get_knowledge_base()
    expected_categories = [
        "ac_motors",
        "dc_motors",
        "pumps_and_valves",
        "transformers",
        "switchgear",
        "ac_dc_drives",
        "gearboxes_and_brake_motors",
        "substation_systems",
        "company_information",
        "industries_and_applications",
        "faqs",
        "troubleshooting_and_installation",
    ]
    for cat in expected_categories:
        data = kb.get_category_data(cat)
        assert data is not None, f"Category '{cat}' was not loaded from knowledge_base directory."
        assert "category" in data
        assert "products" in data or "faqs" in data or "guides" in data or "overview" in data or "key_clients" in data or "company_profile" in data or "sectors" in data


def test_knowledge_base_source_registry():
    """Verify that source_registry.json tracks official PDFs, text extractions, and web sources."""
    kb = get_knowledge_base()
    registry = kb.get_source_registry()
    assert "verified_sources" in registry
    assert len(registry["verified_sources"]) >= 12


def test_knowledge_base_unverified_specifications_tracking():
    """Verify unverified/missing parameters are properly cataloged without hallucination."""
    kb = get_knowledge_base()
    missing_map = kb.get_missing_or_unverified_info()
    assert len(missing_map) > 0
    # Cage Rotor or Wound Rotor should explicitly catalog missing efficiency or frame sizes
    assert any("efficiency" in ";".join(fields).lower() for fields in missing_map.values())


def test_structured_search_matching():
    """Verify keyword and entity search over structured knowledge base."""
    kb = get_knowledge_base()
    res = kb.search_structured_knowledge("wound rotor induction motor", top_n=3)
    assert len(res) > 0
    top = res[0]
    assert top["type"] == "product"
    assert "wound rotor" in top["data"]["product_name"].lower()


def test_multiturn_motor_conversation_flow():
    """
    Test exact multi-turn customer conversation flow:
    Turn 1: "What types of motors do you have?" -> AI: "We offer AC and DC motors. Which type are you interested in?"
    Turn 2: "AC motors." -> AI: continues naturally using relevant AC motor info.
    Turn 3: "What is their maximum power rating?" -> AI: retrieves verified 20,000 kW (20 MW) spec with source citation.
    """
    rag = get_rag_service()

    # Turn 1
    resp1 = rag.answer_question(question="What types of motors do you have?")
    assert "AC and DC motors" in resp1.answer
    assert "Which type are you interested in?" in resp1.answer
    assert resp1.evidence_sufficient is True

    # Turn 2
    history_turn1 = [
        ChatTurn(role="user", content="What types of motors do you have?"),
        ChatTurn(role="assistant", content=resp1.answer),
    ]
    resp2 = rag.answer_question(
        question="AC motors.",
        conversation_history=history_turn1,
    )
    assert resp2.evidence_sufficient is True
    assert "Cage Rotor" in resp2.answer or "Wound Rotor" in resp2.answer or "Flameproof" in resp2.answer

    # Turn 3
    history_turn2 = history_turn1 + [
        ChatTurn(role="user", content="AC motors."),
        ChatTurn(role="assistant", content=resp2.answer),
    ]
    resp3 = rag.answer_question(
        question="What is their maximum power rating?",
        conversation_history=history_turn2,
    )
    assert resp3.evidence_sufficient is True
    # Verified spec: 20,000 kW (20 MW)
    assert "20,000 kW" in resp3.answer or "20000" in resp3.answer or "20 MW" in resp3.answer
    # Verified citation: AC Motors - NIEL Brochure.pdf, Page 1
    assert len(resp3.citations) > 0
    ac_cite = next((c for c in resp3.citations if c.source_filename == "AC Motors - NIEL Brochure.pdf"), None)
    assert ac_cite is not None, "Citation to 'AC Motors - NIEL Brochure.pdf' was not returned."
    assert ac_cite.page_number == 1


def test_transformer_specifications():
    """Verify retrieval of verified transformer ratings (up to 1250 kVA, 33 kV)."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What are the maximum ratings for NIEL distribution transformers?")
    assert resp.evidence_sufficient is True
    assert "1250 kVA" in resp.answer or "33 kV" in resp.answer


def test_dc_motor_ratings():
    """Verify retrieval of DC motor ratings (0.37 kW to 6500 kW)."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What is the power rating range for NIEL DC motors?")
    assert resp.evidence_sufficient is True
    assert "6,500 kW" in resp.answer or "6500" in resp.answer or "3,000 kW" in resp.answer or "3000 kW" in resp.answer


def test_agent_tool_search_product_knowledge_integration():
    """Verify search_product_knowledge tool returns both chunks and structured records."""
    dispatcher = get_tool_dispatcher()
    result = dispatcher.execute_tool(
        "search_product_knowledge",
        {"query": "pumps monoblock head and capacity", "top_k": 3},
    )
    assert result["status"] == "success"
    assert "chunks" in result
    assert "structured_records" in result
    assert len(result["structured_records"]) > 0


def test_abstention_on_unindexed_products_remains_intact():
    """Verify assistant strictly abstains from inventing specs for unindexed goods like ceiling fans."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What are the blade dimensions for NIEL domestic ceiling fans?")
    assert resp.evidence_sufficient is False
    assert "not documented" in resp.answer.lower() or "specializes strictly in industrial" in resp.answer.lower()
