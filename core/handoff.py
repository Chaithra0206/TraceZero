"""Root wrapper for handoff module."""

import importlib.util
import sys
from pathlib import Path

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

target_file = kb_dir / "core" / "handoff.py"
spec = importlib.util.spec_from_file_location("kb_handoff", target_file)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

for _name in dir(mod):
    if not _name.startswith("__"):
        globals()[_name] = getattr(mod, _name)

__all__ = [n for n in dir(mod) if not n.startswith("__")]
