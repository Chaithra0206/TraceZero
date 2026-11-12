"""Security, provenance, conflict resolution policy, and byte-offset validation."""

from __future__ import annotations

import re
from typing import Optional, Tuple

from core.contracts import ClaimStatus, TrustTier
from core.predicates import is_single_valued
from core.storage_api import MemoryStore

INJECTION_REGEX = re.compile(
    r"(?i)("
    r"ignore\s+(all\s+)?previous\s+instructions|"
    r"system\s+prompt|"
    r"system\s+override|"
    r"override\s+policy|"
    r"disregard\s+trust\s+tier|"
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


def apply_policy_and_decide_status(
    store: MemoryStore,
    namespace: str,
    subject: str,
    predicate: str,
    object_val: str,
    origin: str,
    trust_tier: TrustTier,
    raw_quote: str,
    full_text: str = "",
) -> Tuple[ClaimStatus, str, Optional[str]]:
    """Decide claim status based on security policy, trust tiers, and cardinality rules.

    Returns:
        (status, reason, superseded_claim_id)
    """
    # 1. Prompt Injection / Imperative override check
    if (
        INJECTION_REGEX.search(raw_quote)
        or INJECTION_REGEX.search(object_val)
        or (full_text and INJECTION_REGEX.search(full_text))
    ):
        return (
            ClaimStatus.QUARANTINED,
            "Prompt injection or imperative override pattern detected",
            None,
        )

    canon_subj = store.resolve_entity(namespace, subject)
    canon_pred = predicate.strip().lower()

    # 2. Suppression hash check via MemoryStore (cryptographic forgetting tombstone)
    if store.is_suppressed(namespace, canon_subj, canon_pred, object_val) or (
        canon_subj != "user" and store.is_suppressed(namespace, "user", canon_pred, object_val)
    ):
        return (
            ClaimStatus.QUARANTINED,
            "Fact is cryptographically suppressed via deletion tombstone",
            None,
        )

    # 3. Check active existing claims for this (subject, predicate) slot via MemoryStore
    existing_active = store.get_active_claims_for_slot(namespace, canon_subj, canon_pred)

    if is_single_valued(canon_pred):
        for existing in existing_active:
            old_trust = int(existing["trust_tier"])
            if existing["object_val"].strip().lower() != object_val.strip().lower():
                if int(trust_tier) >= old_trust:
                    return (
                        ClaimStatus.ACTIVE,
                        f"Supersedes previous active claim ({existing['claim_id']})",
                        existing["claim_id"],
                    )
                return (
                    ClaimStatus.DISPUTED,
                    f"Contradicts active claim from higher-trust origin ({existing['origin']} tier {old_trust})",
                    None,
                )
            else:
                # Identical value paraphrase/reinforcement: preserve single active claim invariant
                if int(trust_tier) >= old_trust:
                    return (
                        ClaimStatus.ACTIVE,
                        f"Refreshes/deduplicates existing active claim ({existing['claim_id']})",
                        existing["claim_id"],
                    )
                if int(trust_tier) > int(TrustTier.DOC_WEB):
                    return (
                        ClaimStatus.SUPERSEDED,
                        f"Corroborates higher-trust active claim ({existing['claim_id']})",
                        None,
                    )

        if int(trust_tier) <= int(TrustTier.DOC_WEB) or origin.lower() in ("doc", "web"):
            return (
                ClaimStatus.QUARANTINED,
                "Untrusted origin claim quarantined pending user verification",
                None,
            )

        return ClaimStatus.ACTIVE, "New active claim accepted", None

    # Multi-valued predicate
    if int(trust_tier) <= int(TrustTier.DOC_WEB) or origin.lower() in ("doc", "web"):
        return (
            ClaimStatus.QUARANTINED,
            "Untrusted multi-valued claim quarantined pending verification",
            None,
        )

    return ClaimStatus.ACTIVE, "New multi-valued claim accepted", None
