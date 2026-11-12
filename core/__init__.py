"""Root wrapper for core module."""

from pathlib import Path
import sys

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

kb_core_dir = str(kb_dir / "core")
if kb_core_dir not in __path__:
    __path__.append(kb_core_dir)

from core.contracts import (
    ClaimRecord,
    ClaimStatus,
    DeletionReceipt,
    HandoffPacket,
    RecallResult,
    RetrievalResult,
    SourceRecord,
    SourceSpan,
    TrustTier,
)
from core.forget import forget_target
from core.ingest import ingest_message
from core.retrieval import recall_context
from core.storage_api import (
    MemoryStore,
    embed_text,
    get_embedder,
    get_claim_history,
    explain_claim,
    list_quarantined,
    confirm_quarantined_claim,
    run_readonly_sql,
    list_namespaces,
)
from core.handoff import (
    create_handoff,
    get_handoff,
)
from core.bridge import (
    remember,
    recall,
    explain,
    history,
    quarantine_list,
    confirm_quarantine,
    forget,
    verify_deletion,
    handoff_create,
    handoff_get,
)

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
    "list_namespaces",
    "TrustTier",
    "ClaimStatus",
    "ClaimRecord",
    "SourceRecord",
    "SourceSpan",
    "RetrievalResult",
    "RecallResult",
    "DeletionReceipt",
    "HandoffPacket",
    "create_handoff",
    "get_handoff",
    "remember",
    "recall",
    "explain",
    "history",
    "quarantine_list",
    "confirm_quarantine",
    "forget",
    "verify_deletion",
    "handoff_create",
    "handoff_get",
]
