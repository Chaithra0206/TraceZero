"""Root wrapper for seed_mock_shard."""

import importlib.util
import sys
from pathlib import Path

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

target_file = kb_dir / "core" / "seed_mock_shard.py"
spec = importlib.util.spec_from_file_location("kb_seed_mock_shard", target_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

main = mod.main

if __name__ == "__main__":
    main()
