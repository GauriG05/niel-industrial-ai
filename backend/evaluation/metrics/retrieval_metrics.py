"""Information retrieval metrics for RAG evaluation.

Implements Recall@K, Precision@K, Mean Reciprocal Rank (MRR),
and Normalized Discounted Cumulative Gain (nDCG@K).
"""

from typing import Iterable, List, Sequence, Set
import math
import re


def _clean_stem(name: str) -> str:
    """Normalize file name by stripping extension and non-alphanumeric chars."""
    if not name:
        return ""
    clean = re.sub(r"\.(pdf|txt|json|md)$", "", str(name).strip().lower(), flags=re.IGNORECASE)
    clean = re.sub(r"[^\w\d]", "", clean)
    return clean


def _is_item_match(retrieved: str, relevant: str) -> bool:
    """Check if retrieved document matches expected document (accounting for .txt/.pdf and naming variants)."""
    s_ret = _clean_stem(retrieved)
    s_rel = _clean_stem(relevant)
    if not s_ret or not s_rel:
        return False
    return s_ret == s_rel or s_ret in s_rel or s_rel in s_ret


def recall_at_k(
    retrieved_items: Sequence[str],
    relevant_items: Iterable[str],
    k: int = 5,
) -> float:
    """Calculate Recall@K: proportion of relevant items retrieved in top K."""
    rel_list = [item for item in relevant_items if item]
    if not rel_list:
        return 1.0  # vacuously satisfied when no specific item required

    top_k = retrieved_items[:k]
    hits = sum(1 for rel in rel_list if any(_is_item_match(ret, rel) for ret in top_k))
    return hits / len(rel_list)


def precision_at_k(
    retrieved_items: Sequence[str],
    relevant_items: Iterable[str],
    k: int = 5,
) -> float:
    """Calculate Precision@K: proportion of top K items that are relevant."""
    if k <= 0:
        return 0.0
    rel_list = [item for item in relevant_items if item]
    if not rel_list:
        return 1.0

    top_k = retrieved_items[:k]
    hits = sum(1 for ret in top_k if any(_is_item_match(ret, rel) for rel in rel_list))
    return hits / min(k, len(top_k)) if top_k else 0.0


def reciprocal_rank(
    retrieved_items: Sequence[str],
    relevant_items: Iterable[str],
) -> float:
    """Calculate Reciprocal Rank (1 / rank of first relevant document)."""
    rel_list = [item for item in relevant_items if item]
    if not rel_list:
        return 1.0

    for idx, ret in enumerate(retrieved_items, start=1):
        if any(_is_item_match(ret, rel) for rel in rel_list):
            return 1.0 / idx
    return 0.0


def ndcg_at_k(
    retrieved_items: Sequence[str],
    relevant_items: Iterable[str],
    k: int = 5,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K (nDCG@K)."""
    rel_list = [item for item in relevant_items if item]
    if not rel_list:
        return 1.0

    top_k = retrieved_items[:k]
    if not top_k:
        return 0.0

    # DCG
    dcg = 0.0
    for idx, ret in enumerate(top_k):
        gain = 1.0 if any(_is_item_match(ret, rel) for rel in rel_list) else 0.0
        dcg += gain / math.log2(idx + 2)

    # Ideal DCG
    idcg = 0.0
    num_ideal = min(k, len(rel_list))
    for idx in range(num_ideal):
        idcg += 1.0 / math.log2(idx + 2)

    return (dcg / idcg) if idcg > 0.0 else 0.0
