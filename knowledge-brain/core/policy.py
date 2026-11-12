"""Security, provenance, conflict resolution policy, and byte-offset validation."""

from __future__ import annotations

import hashlib
import hmac
import re
import sqlite3
from typing import Optional, Tuple

from core.contracts import Cardinality, ORIGIN_TRUST_MAP, PREDICATE_REGISTRY


HMAC_SECRET = b"knowledge_brain_enterprise_hmac_secret_2026"

INJECTION_REGEX = re.compile(
    r"(?i)("
    r"ignore\s+(all\s+)?previous\s+instructions|"
    r"system\s+prompt|"
    r"override\s+policy|"
    r"always\s+answer|"
    r"bypass\s+safety|"
    r"you\s+are\s+now|"
    r"disregard\s+(all\s+)?prior|"
    r"jailbreak|"
    r"exfiltrate|"
    r"delete\s+all\s+files|"
    r"act\s+as\s+root"
    r")"
)


def verify_exact_quote_span(raw_text: str, exact_quote: str) -> Optional[Tuple[int, int]]:
    """Find exact_quote verbatim in raw_text and calculate exact UTF-8 byte offsets.

    Returns (byte_start, byte_end) if verbatim match is found; returns None if
    quote does not exist in raw_text (rejecting hallucinated quotes).
    Properly handles multi-byte UTF-8 characters (e.g., emojis, non-ASCII currency).
    """
    if not exact_quote or not raw_text:
        return None

    char_idx = raw_text.find(exact_quote)
    if char_idx == -1:
        return None

    raw_bytes = raw_text.encode("utf-8")
    byte_start = len(raw_text[:char_idx].encode("utf-8"))
    byte_end = byte_start + len(exact_quote.encode("utf-8"))

    if raw_bytes[byte_start:byte_end].decode("utf-8") != exact_quote:
        return None

    return byte_start, byte_end


def compute_fact_hmac(subject: str, predicate: str, object_val: str, key: bytes = HMAC_SECRET) -> str:
    """Compute HMAC-SHA256 signature for a triple to prevent re-learning forgotten facts."""
    norm_s = subject.strip().lower()
    norm_p = predicate.strip().lower()
    norm_o = object_val.strip().lower()
    payload = f"{norm_s}|{norm_p}|{norm_o}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def is_suppressed(conn: sqlite3.Connection, fact_hmac: str) -> bool:
    """Check if a fact HMAC is present in suppression_hashes."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM suppression_hashes WHERE fact_hmac = ?", (fact_hmac,))
    return cursor.fetchone() is not None


def apply_policy_and_decide_status(
    conn: sqlite3.Connection,
    namespace: str,
    subject: str,
    predicate: str,
    object_val: str,
    origin: str,
    trust_tier: int,
    raw_quote: str,
) -> Tuple[str, Optional[str], Optional[str]]:
    """Decide claim status based on security policy, trust tiers, and cardinality rules.

    Returns:
        (status, reason, superseded_claim_id)
        status in ('active', 'superseded', 'disputed', 'quarantined')
    """
    # 1. Prompt Injection / Imperative override check
    if INJECTION_REGEX.search(raw_quote) or INJECTION_REGEX.search(object_val):
        return "quarantined", "Prompt injection or imperative override pattern detected", None

    # 2. Suppression hash check (cryptographic forgetting tombstone)
    # Check both specific subject and canonical 'user' / wildcard
    fact_hmac_subj = compute_fact_hmac(subject, predicate, object_val)
    fact_hmac_user = compute_fact_hmac("user", predicate, object_val)
    if is_suppressed(conn, fact_hmac_subj) or is_suppressed(conn, fact_hmac_user):
        return "quarantined", "Fact is cryptographically suppressed via deletion tombstone", None

    # 3. Lookup predicate cardinality
    meta = PREDICATE_REGISTRY.get(predicate)
    cardinality = meta.cardinality if meta else Cardinality.MULTI

    # 4. Check for active existing claims
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.claim_id, c.object_val, c.source_id, s.trust_tier, s.origin
        FROM claims_index c
        JOIN sources_index s ON c.source_id = s.source_id
        WHERE c.namespace = ? AND c.subject = ? AND c.predicate = ? AND c.status = 'active'
        """,
        (namespace, subject, predicate),
    )
    existing_active = cursor.fetchall()

    if cardinality == Cardinality.SINGLE:
        for existing in existing_active:
            if existing["object_val"].strip().lower() != object_val.strip().lower():
                old_trust = existing["trust_tier"]
                # Single-valued conflict resolution:
                if trust_tier >= old_trust:
                    return "active", f"Supersedes previous active claim ({existing['claim_id']})", existing["claim_id"]
                else:
                    return "disputed", f"Contradicts active claim from higher-trust origin ({existing['origin']} tier {old_trust})", None

        # No conflicting active claim found:
        if trust_tier == 1 or origin in ("doc", "web"):
            return "quarantined", "Untrusted origin claim quarantined pending user verification", None

        return "active", "New active claim accepted", None

    else:
        # Multi-valued predicate:
        if trust_tier == 1 or origin in ("doc", "web"):
            return "quarantined", "Untrusted multi-valued claim quarantined pending verification", None

        return "active", "New multi-valued claim accepted", None
