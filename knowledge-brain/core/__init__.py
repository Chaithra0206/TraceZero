"""Knowledge Brain unified core engine facade."""

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
from core.storage_api import MemoryStore

__all__ = [
    "MemoryStore",
    "ingest_message",
    "recall_context",
    "forget_target",
    "TrustTier",
    "ClaimStatus",
    "ClaimRecord",
    "SourceRecord",
    "RetrievalResult",
    "DeletionReceipt",
    "HandoffPacket",
]
