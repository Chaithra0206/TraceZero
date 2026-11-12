"""Automated verification tests for Role 4 evaluation harness (live MemoryStore + handoff + 5 strategies)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evals.compare_baselines import run_baseline_comparison
from evals.run_5_strategies import evaluate_5_strategies
from evals.run_mvs_eval import run_mvs_eval
from evals.seed_30_sessions import generate_dataset


def test_role4_dataset_rubric_cases() -> None:
    dataset = generate_dataset()
    assert dataset["metadata"]["num_employees"] == 100
    assert dataset["metadata"]["num_sessions"] == 30
    assert dataset["metadata"]["target_namespace"] == "acme_corp/users/emp_042"
    categories = {
        m.get("category")
        for sess in dataset["emp_042_sessions"]
        for m in sess["messages"]
    }
    assert "aws_region_paraphrase" in categories
    assert "db_initial_user" in categories
    assert "db_valid_update_user" in categories
    assert "db_contradiction_doc" in categories
    assert "prompt_injection_web" in categories
    assert "deletion_secret" in categories
    assert "task_state" in categories


def test_role4_mvs_restart_handoff_and_deletion(tmp_path: Path) -> None:
    mvs = run_mvs_eval(memory_root=tmp_path, subprocess_restart=True)
    assert mvs["sessions_seeded"] >= 30
    assert mvs["process_restart_verified"] is True
    assert mvs["handoff_tokens"] < 350
    assert mvs["residual_shard_bytes"] == 0
    assert mvs["post_deletion_probes_abstained"] == 10
    assert mvs["stored_deletion_receipt"]["byte_scan_matches"] == 0
    assert mvs["never_stored_deletion_receipt"]["byte_scan_matches"] == 0


def test_role4_five_strategies_and_baselines_live(tmp_path: Path) -> None:
    report = evaluate_5_strategies(mode="live", memory_root=tmp_path)
    assert "Prompt-stuffed" in report
    assert "Pure Vector (sqlite-vec)" in report
    assert "Claims / Knowledge Graph" in report
    assert "OKF Files (.okf.md)" in report
    assert "SQL / Code (run_readonly_sql)" in report
    assert "Hybrid Scoped Engine" in report

    comp = run_baseline_comparison(mode="live")
    assert comp["knowledge_brain"]["accuracy_pct"] == 100.0
    assert comp["knowledge_brain"]["byte_clean_deletion_pct"] == 100.0
    assert comp["full_history_30_sessions"]["byte_clean_deletion_pct"] == 0.0
    assert comp["naive_vector_rag"]["byte_clean_deletion_pct"] == 0.0

    results_dir = ROOT_DIR / "evals" / "results"
    assert (results_dir / "benchmark_report.md").exists()
    metrics = json.loads((results_dir / "metrics.json").read_text(encoding="utf-8"))
    assert len(metrics["five_strategy_matrix"]) == 6
    assert (results_dir / "deletion_receipts.json").exists()
