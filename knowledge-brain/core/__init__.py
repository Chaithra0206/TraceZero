"""Knowledge Brain core module."""

from core.contracts import (
    ClaimRecord,
    DeletionReceipt,
    HandoffPacket,
    RecallResult,
    SourceSpan,
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
    "SourceSpan",
    "ClaimRecord",
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
