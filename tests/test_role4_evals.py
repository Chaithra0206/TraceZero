"""Root test wrapper importing Role 4 evaluation tests."""

import importlib.util
import sys
from pathlib import Path

kb_dir = Path(__file__).resolve().parent.parent / "knowledge-brain"
if str(kb_dir) not in sys.path:
    sys.path.insert(0, str(kb_dir))

target_file = kb_dir / "tests" / "test_role4_evals.py"
spec = importlib.util.spec_from_file_location("kb_test_role4_evals", target_file)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

test_role4_dataset_rubric_cases = mod.test_role4_dataset_rubric_cases
test_role4_mvs_restart_handoff_and_deletion = mod.test_role4_mvs_restart_handoff_and_deletion
test_role4_five_strategies_and_baselines_live = mod.test_role4_five_strategies_and_baselines_live
