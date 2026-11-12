"""Root wrapper for contracts."""

import importlib.util
import sys
from pathlib import Path

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

target_file = kb_dir / "core" / "contracts.py"
spec = importlib.util.spec_from_file_location("kb_contracts", target_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SourceSpan = mod.SourceSpan
ClaimRecord = mod.ClaimRecord
RecallResult = mod.RecallResult
DeletionReceipt = mod.DeletionReceipt
HandoffPacket = mod.HandoffPacket

__all__ = [
    "SourceSpan",
    "ClaimRecord",
    "RecallResult",
    "DeletionReceipt",
    "HandoffPacket",
]
