"""Tests for site_url_map and live product URL integration in chat responses."""

import pytest
from fastapi.testclient import TestClient

from backend.app.knowledge.site_url_map import (
    BASE_SITE_URL,
    CATEGORY_URL_MAP,
    PRODUCT_ID_URL_MAP,
    resolve_site_url,
)
from backend.app.main import app
from backend.app.schemas.chat import ChatResponse
from backend.app.services.rag_service import get_rag_service

client = TestClient(app)


def test_base_url_valid():
    """Verify base site URL matches official domain."""
    assert BASE_SITE_URL == "https://newindiaelectricals.com"


def test_product_id_mappings():
    """Verify product IDs from knowledge base map to valid live URLs."""
    expected_mappings = {
        "ac-cage-rotor": f"{BASE_SITE_URL}/ac-motors/closed-cage-type-motors/",
        "ac-flameproof": f"{BASE_SITE_URL}/ac-motors/flame-proof-motors/",
        "transformer-distribution": f"{BASE_SITE_URL}/transformers/distribution-transformer/",
        "pump-end-suction-monoblock": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/end-suction-monoblock-pump/",
        "switchgear-power-plus-v": f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-v/",
        "drive-lv-ac": f"{BASE_SITE_URL}/low-voltage-ac-drives/",
        "dc-industrial-motors": f"{BASE_SITE_URL}/dc-motors/",
    }
    for prod_id, expected_url in expected_mappings.items():
        assert prod_id in PRODUCT_ID_URL_MAP
        assert resolve_site_url(product_id=prod_id) == expected_url


def test_category_mappings():
    """Verify category identifiers resolve to correct category-level pages."""
    assert resolve_site_url(category="ac_motors") == f"{BASE_SITE_URL}/ac-motors/"
    assert resolve_site_url(category="AC Motors") == f"{BASE_SITE_URL}/ac-motors/"
    assert resolve_site_url(category="dc_motors") == f"{BASE_SITE_URL}/dc-motors/"
    assert resolve_site_url(category="transformers") == f"{BASE_SITE_URL}/transformers/"
    assert resolve_site_url(category="switchgear") == f"{BASE_SITE_URL}/switchgear-panels/"
    assert resolve_site_url(category="pumps_and_valves") == f"{BASE_SITE_URL}/pumps-valves/"
    assert resolve_site_url(category="drives") == f"{BASE_SITE_URL}/drives/"
    assert resolve_site_url(category="substation_systems") == f"{BASE_SITE_URL}/substation-systems/"


def test_subtype_query_resolution():
    """Verify specific subtype keywords in query strings resolve to deep links."""
    assert resolve_site_url(text="We need flameproof motors for a hazardous gas area") == f"{BASE_SITE_URL}/ac-motors/flame-proof-motors/"
    assert resolve_site_url(text="Tell me about crane duty slipring motors") == f"{BASE_SITE_URL}/ac-motors/crane-duty-slipring-motors/"
    assert resolve_site_url(text="What is the power rating of furnace transformers?") == f"{BASE_SITE_URL}/transformers/furnace-transformer/"
    assert resolve_site_url(text="Specifications for vacuum pumps") == f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/vacuum-pumps/"
    assert resolve_site_url(text="Tell me about containerised secondary substations css") == f"{BASE_SITE_URL}/transformers/containerised-secondary-substations-css/"


def test_non_product_queries_return_none():
    """Verify that unconfident or non-product queries do not fabricate URLs."""
    assert resolve_site_url(text="Hello, good morning!") is None
    assert resolve_site_url(text="What is the weather in Bangalore?") is None
    assert resolve_site_url(text="Can I get a discount or pricing in USD?") is None
    assert resolve_site_url() is None


def test_chat_response_schema_contains_site_url():
    """Verify ChatResponse model supports optional site_url."""
    resp = ChatResponse(
        answer="Sample answer",
        evidence_sufficient=True,
        request_id="test-123",
        site_url=f"{BASE_SITE_URL}/ac-motors/",
    )
    assert resp.site_url == f"{BASE_SITE_URL}/ac-motors/"

    resp_no_url = ChatResponse(
        answer="Sample answer without URL",
        evidence_sufficient=False,
        request_id="test-124",
    )
    assert resp_no_url.site_url is None


def test_chat_response_attaches_site_url_for_ac_motors():
    """Verify RAG service populates site_url for AC motor queries."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What is the maximum power rating for NIEL AC Motors?")
    assert resp.evidence_sufficient is True
    assert resp.site_url is not None
    assert resp.site_url.startswith(f"{BASE_SITE_URL}/ac-motors/")


def test_chat_response_omits_site_url_on_pricing_abstention():
    """Verify RAG service omits site_url when abstaining on unsupported pricing."""
    rag = get_rag_service()
    resp = rag.answer_question(question="What is the price in USD and discount for a 50 kW motor?")
    assert resp.evidence_sufficient is False
    assert resp.site_url is None

