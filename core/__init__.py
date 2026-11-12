"""Root wrapper for core module."""

from core.contracts import (
    SourceSpan,
    ClaimRecord,
    RecallResult,
    DeletionReceipt,
    HandoffPacket,
)
from core.handoff import (
    create_handoff,
    get_handoff,
)

__all__ = [
    "SourceSpan",
    "ClaimRecord",
    "RecallResult",
    "DeletionReceipt",
    "HandoffPacket",
    "create_handoff",
    "get_handoff",
]
