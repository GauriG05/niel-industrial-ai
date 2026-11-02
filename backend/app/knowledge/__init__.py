"""Knowledge base package for structured NIEL industrial records."""

from backend.app.knowledge.knowledge_base import get_knowledge_base, NIELKnowledgeBase
from backend.app.knowledge.site_url_map import resolve_site_url, BASE_SITE_URL

__all__ = ["get_knowledge_base", "NIELKnowledgeBase", "resolve_site_url", "BASE_SITE_URL"]
