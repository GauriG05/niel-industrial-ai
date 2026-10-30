"""Content hashing and deduplication utilities."""

import hashlib


def compute_sha256_bytes(content: bytes) -> str:
    """Compute deterministic SHA-256 hash of raw bytes."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def compute_sha256_text(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return compute_sha256_bytes(text.encode("utf-8"))

