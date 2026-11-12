"""Knowledge Brain unified core engine facade."""

from typing import Any, Dict, List, Optional

from core.contracts import (
    ClaimRecord,
    ClaimStatus,
    DeletionReceipt,
    HandoffPacket,
    RetrievalResult,
    SourceRecord,
    TrustTier,
)
from core.forget import forget_target
from core.ingest import ingest_message
from core.retrieval import recall_context
from core.storage_api import MemoryStore, embed_text, get_embedder


def get_claim_history(
    store: MemoryStore, namespace: str, subject: str, predicate: Optional[str] = None
) -> List[Dict[str, Any]]:
    return store.get_claim_history(namespace, subject, predicate)


def explain_claim(store: MemoryStore, namespace: str, claim_id: str) -> Dict[str, Any]:
    return store.explain_claim(namespace, claim_id)


def list_quarantined(store: MemoryStore, namespace: str) -> List[Dict[str, Any]]:
    return store.list_quarantined(namespace)


def confirm_quarantined_claim(store: MemoryStore, namespace: str, claim_id: str) -> bool:
    return store.confirm_quarantined_claim(namespace, claim_id)


def run_readonly_sql(
    store: MemoryStore, namespace: str, sql_query: str, params: tuple = ()
) -> List[Dict[str, Any]]:
    return store.run_readonly_sql(namespace, sql_query, params)


__all__ = [
    "MemoryStore",
    "embed_text",
    "get_embedder",
    "ingest_message",
    "recall_context",
    "forget_target",
    "get_claim_history",
    "explain_claim",
    "list_quarantined",
    "confirm_quarantined_claim",
    "run_readonly_sql",
    "TrustTier",
    "ClaimStatus",
    "ClaimRecord",
    "SourceRecord",
    "RetrievalResult",
    "DeletionReceipt",
    "HandoffPacket",
]
