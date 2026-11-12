"""Root wrapper for core.bridge module."""

import importlib.util
import sys
from pathlib import Path

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

target_file = kb_dir / "core" / "bridge.py"
spec = importlib.util.spec_from_file_location("kb_bridge", target_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

remember = mod.remember
recall = mod.recall
explain = mod.explain
history = mod.history
quarantine_list = mod.quarantine_list
confirm_quarantine = mod.confirm_quarantine
forget = mod.forget
verify_deletion = mod.verify_deletion
handoff_create = mod.handoff_create
handoff_get = mod.handoff_get

__all__ = [
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
