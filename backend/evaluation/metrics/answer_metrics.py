"""Evaluation metrics for RAG answer quality, faithfulness, citations, and abstention."""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set
import re


def _normalize_text(text: str) -> str:
    """Normalize text for robust substring and keyword comparison."""
    if not text:
        return ""
    # Lowercase and remove commas from numbers (e.g. 20,000 -> 20000)
    text = re.sub(r"(\d+),(\d+)", r"\1\2", str(text).lower())
    # Collapse letter-digit spacing (e.g. "ip 22" -> "ip22", "ic 411" -> "ic411")
    text = re.sub(r"([a-z]+)\s+(\d+)", r"\1\2", text)
    # Collapse digit-unit spacing (e.g. "415 v" -> "415v", "250 kw" -> "250kw")
    text = re.sub(r"(\d+)\s+(v|kv|kw|mva|kva|rpm|hz|hp)\b", r"\1\2", text)
    text = re.sub(r"[^\w\d\.\-\+/%]", " ", text)
    return " ".join(text.split())


def _extract_content_tokens(text: str) -> Set[str]:
    """Extract informative non-stopword tokens."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "is", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "can", "could", "shall", "should",
        "will", "would", "may", "might", "must", "that", "which", "who", "whom",
        "this", "these", "those", "am", "it", "its", "as", "from", "up", "about",
        "into", "over", "after", "your", "our", "their", "we", "you", "they", "i"
    }
    tokens = set()
    for tok in re.findall(r"\b[\w\.\-\+/%]{2,}\b", text.lower()):
        if tok not in stop_words:
            tokens.add(tok)
    return tokens


def evaluate_answer_correctness(
    generated_answer: str,
    expected_keywords: Sequence[str],
    reference_facts: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Evaluate factual correctness based on presence of expected facts and keywords."""
    norm_answer = _normalize_text(generated_answer)
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []

    for kw in expected_keywords:
        norm_kw = _normalize_text(kw)
        # Check if direct match or if comma-separated / slash-separated variants match
        variants = [norm_kw] + [v.strip() for v in norm_kw.split("/") if v.strip()]
        if any(v in norm_answer for v in variants):
            matched_keywords.append(kw)
        else:
            # Also check individual word tokens
            kw_tokens = norm_kw.split()
            if kw_tokens and all(t in norm_answer for t in kw_tokens):
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)

    total_kws = len(expected_keywords)
    keyword_coverage = (len(matched_keywords) / total_kws) if total_kws > 0 else 1.0

    # Fact token overlap
    total_facts = len(reference_facts or [])
    if total_facts > 0:
        fact_scores = []
        answer_tokens = _extract_content_tokens(norm_answer)
        for fact in (reference_facts or []):
            fact_tokens = _extract_content_tokens(fact)
            if fact_tokens:
                overlap = len(fact_tokens & answer_tokens) / len(fact_tokens)
                fact_scores.append(overlap)
            else:
                fact_scores.append(1.0)
        fact_score = sum(fact_scores) / len(fact_scores)
    else:
        fact_score = keyword_coverage

    composite_score = (keyword_coverage * 0.5) + (fact_score * 0.5)
    is_correct = (keyword_coverage >= 0.5) or (composite_score >= 0.5) if total_kws > 0 else True

    return {
        "score": round(composite_score, 4),
        "keyword_coverage": round(keyword_coverage, 4),
        "fact_score": round(fact_score, 4),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "is_correct": is_correct,
    }


def evaluate_faithfulness(
    generated_answer: str,
    retrieved_contexts: Sequence[str],
) -> Dict[str, Any]:
    """Evaluate whether generated claims are supported by retrieved context."""
    if not generated_answer.strip():
        return {"score": 1.0, "is_faithful": True, "unsupported_claims": []}

    combined_context = _normalize_text(" ".join(retrieved_contexts))
    sentences = re.split(r"[.\n;!?]", generated_answer)
    unsupported_claims: List[str] = []
    total_checkable_sentences = 0
    supported_sentences = 0

    for raw_s in sentences:
        s = raw_s.strip()
        if len(s) < 15:
            continue
        technical_tokens = re.findall(r"\b\d+[\w\.\-/%]*\b", s.lower())
        if not technical_tokens:
            continue

        total_checkable_sentences += 1
        tokens_found = sum(1 for t in technical_tokens if t in combined_context)
        token_ratio = tokens_found / len(technical_tokens)

        if token_ratio >= 0.4:
            supported_sentences += 1
        else:
            unsupported_claims.append(s)

    if total_checkable_sentences == 0:
        score = 1.0
    else:
        score = supported_sentences / total_checkable_sentences

    return {
        "score": round(score, 4),
        "is_faithful": score >= 0.70,
        "unsupported_claims": unsupported_claims,
    }


def evaluate_citation_accuracy(
    citations: Sequence[Any],
    expected_sources: Sequence[str],
    expected_pages: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Evaluate whether the answer references expected files and pages."""
    cited_sources = set()
    cited_pages = set()
    for c in citations:
        src = getattr(c, "source_filename", None) or (c.get("source_filename") if isinstance(c, dict) else None) or getattr(c, "source", None) or (c.get("source") if isinstance(c, dict) else None)
        if src:
            clean_src = re.sub(r"\.(pdf|txt)$", "", str(src).strip().lower(), flags=re.IGNORECASE)
            clean_src = re.sub(r"[^\w\d]", "", clean_src)
            cited_sources.add(clean_src)
        pg = getattr(c, "page_number", None) if not isinstance(c, dict) else c.get("page_number")
        if pg is None:
            pg = getattr(c, "page", None) if not isinstance(c, dict) else c.get("page")
        if pg is not None:
            try:
                cited_pages.add(int(pg))
            except (ValueError, TypeError):
                pass

    if not expected_sources and not expected_pages:
        return {
            "score": 1.0,
            "source_hit": True,
            "page_hit": True,
            "cited_sources": list(cited_sources),
            "cited_pages": list(cited_pages),
        }

    # Match source filenames
    source_hits = 0
    for src in expected_sources:
        clean_exp = re.sub(r"\.(pdf|txt)$", "", str(src).strip().lower(), flags=re.IGNORECASE)
        clean_exp = re.sub(r"[^\w\d]", "", clean_exp)
        if any(clean_exp in cs or cs in clean_exp for cs in cited_sources):
            source_hits += 1
    source_score = (source_hits / len(expected_sources)) if expected_sources else 1.0

    page_hits = 0
    if expected_pages:
        for pg in expected_pages:
            if pg in cited_pages:
                page_hits += 1
        page_score = page_hits / len(expected_pages)
    else:
        page_score = 1.0

    composite = (source_score * 0.7) + (page_score * 0.3)
    return {
        "score": round(composite, 4),
        "source_hit": source_score > 0.0,
        "page_hit": page_score > 0.0,
        "cited_sources": list(cited_sources),
        "cited_pages": list(cited_pages),
    }


def evaluate_abstention(
    should_abstain: bool,
    generated_answer: str,
    evidence_sufficient: bool,
) -> Dict[str, Any]:
    """Evaluate whether the assistant correctly abstains when information is absent."""
    norm_answer = _normalize_text(generated_answer)
    
    abstention_indicators = [
        "not available",
        "not documented",
        "please contact",
        "contact our sales",
        "consult niel",
        "reach out to",
        "knowledge base does not contain",
        "information is not available",
        "not mentioned",
        "human support",
        "does not provide details",
        "no information",
        "does not specify",
        "cannot provide",
        "cant provide",
        "does not state",
        "not published",
        "commercial quotes depend",
        "not publish",
        "feel free to contact",
    ]
    detected_abstention = any(ind in norm_answer for ind in abstention_indicators) or (not evidence_sufficient)

    if should_abstain:
        is_correct = detected_abstention
    else:
        is_correct = evidence_sufficient

    return {
        "should_abstain": should_abstain,
        "detected_abstention": detected_abstention,
        "evidence_sufficient": evidence_sufficient,
        "is_correct": is_correct,
    }
