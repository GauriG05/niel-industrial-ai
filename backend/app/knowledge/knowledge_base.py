"""Structured NIEL Industrial Knowledge Base loader and query engine."""

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class NIELKnowledgeBase:
    """Manages the 12 structured knowledge categories and verified source registry."""

    def __init__(self, kb_dir: Optional[Path] = None):
        settings = get_settings()
        self.kb_dir = kb_dir or (settings.DATA_DIR / "knowledge_base")
        self.categories_data: Dict[str, Dict[str, Any]] = {}
        self.source_registry: Dict[str, Any] = {}
        self._load_knowledge()

    def _load_knowledge(self):
        """Load all structured JSON files from the knowledge base directory."""
        if not self.kb_dir.exists():
            logger.warning("Knowledge base directory %s does not exist.", self.kb_dir)
            return

        registry_file = self.kb_dir / "source_registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    self.source_registry = json.load(f)
            except Exception as exc:
                logger.error("Failed to load source_registry.json: %s", exc)

        # Load all category JSON files
        for json_file in sorted(self.kb_dir.glob("*.json")):
            if json_file.name == "source_registry.json":
                continue
            category_key = json_file.stem  # e.g. "ac_motors"
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.categories_data[category_key] = data
            except Exception as exc:
                logger.error("Failed to load knowledge file %s: %s", json_file.name, exc)

        logger.info("Loaded %d knowledge base categories from %s", len(self.categories_data), self.kb_dir)

    def get_all_categories(self) -> List[str]:
        """List all top-level categories available in the knowledge base."""
        return [data.get("category", key) for key, data in self.categories_data.items()]

    def get_category_data(self, category_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete structured data for a given category key."""
        clean_key = category_key.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        if clean_key in self.categories_data:
            return self.categories_data[clean_key]
        for k, v in self.categories_data.items():
            if v.get("category", "").lower() == category_key.lower():
                return v
        return None

    def search_structured_knowledge(self, query: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Keyword and entity search over structured knowledge records.
        Returns matching product records, FAQs, or troubleshooting blocks.
        """
        stopwords = {"what", "which", "where", "does", "niel", "the", "for", "with", "and", "are", "have", "you", "tell", "about"}
        query_words = set(w for w in re.findall(r"\w+", query.lower()) if len(w) > 1 and w not in stopwords)
        matches: List[tuple[int, Dict[str, Any]]] = []

        q_lower = query.lower()

        for cat_key, cat_data in self.categories_data.items():
            cat_name = cat_data.get("category", "")
            cat_match = 3 if any(w in cat_name.lower() for w in query_words) else 0
            
            # 1. Search products
            for prod in cat_data.get("products", []):
                prod_name = prod.get("product_name", "").lower()
                p_text = f"{prod_name} {prod.get('description', '')} {json.dumps(prod.get('specifications', {}))} {json.dumps(prod.get('applications', []))}".lower()
                prod_words = set(re.findall(r"\w+", p_text))
                overlap = len(query_words.intersection(prod_words))
                if overlap > 0:
                    score = overlap * 2 + cat_match
                    if any(w in prod_name for w in query_words):
                        score += 5
                    # Give extra score if specific distinctive term matches
                    if "dc" in query_words and "dc" in prod_name:
                        score += 10
                    if "ac" in query_words and "ac" in prod_name:
                        score += 5
                    matches.append((score, {
                        "type": "product",
                        "category": cat_name,
                        "data": prod,
                    }))

            # 2. Search FAQs
            for faq in cat_data.get("faqs", []):
                faq_q = faq.get("question", "").lower()
                f_text = f"{faq_q} {faq.get('answer', '')}".lower()
                f_words = set(re.findall(r"\w+", f_text))
                overlap = len(query_words.intersection(f_words))
                if overlap > 0:
                    score = overlap * 2
                    if any(w in faq_q for w in query_words):
                        score += 3
                    matches.append((score, {
                        "type": "faq",
                        "category": cat_name,
                        "data": faq,
                    }))

            # 3. Search Troubleshooting Guides
            for guide in cat_data.get("guides", []):
                topic = guide.get("topic", "").lower()
                g_text = f"{topic} {json.dumps(guide.get('procedure', []))}".lower()
                g_words = set(re.findall(r"\w+", g_text))
                overlap = len(query_words.intersection(g_words))
                if overlap > 0:
                    score = overlap * 2
                    if any(w in topic for w in query_words):
                        score += 4
                    matches.append((score, {
                        "type": "troubleshooting",
                        "category": cat_name,
                        "data": guide,
                    }))

        # Sort descending by match score
        matches.sort(key=lambda m: m[0], reverse=True)
        return [m[1] for m in matches[:top_n]]

    def get_missing_or_unverified_info(self) -> Dict[str, List[str]]:
        """Compile a dictionary of unverified or missing technical parameters by product."""
        missing_map: Dict[str, List[str]] = {}
        for cat_key, cat_data in self.categories_data.items():
            for prod in cat_data.get("products", []):
                p_name = prod.get("product_name", prod.get("id"))
                unverified = prod.get("unverified_fields", [])
                if unverified:
                    missing_map[p_name] = unverified
        return missing_map

    def get_source_registry(self) -> Dict[str, Any]:
        """Return verified source registry mapping."""
        return self.source_registry


_kb_instance: Optional[NIELKnowledgeBase] = None


def get_knowledge_base() -> NIELKnowledgeBase:
    """Singleton accessor for NIELKnowledgeBase."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = NIELKnowledgeBase()
    return _kb_instance
