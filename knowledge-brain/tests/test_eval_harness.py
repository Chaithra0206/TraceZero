"""Unit tests for the Knowledge Brain Role 4 evaluation harness, TokenLedger, and mock engine."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from evals.compare_baselines import run_baseline_comparison
from evals.mock_engine import (
    forget_target,
    ingest_message,
    recall_context,
    reset_mock_engine,
)
from evals.run_5_strategies import evaluate_5_strategies
from evals.run_benchmarks import _wrap_live_contract, run_benchmark_suite
from evals.run_mvs_eval import run_benchmark_suite as mvs_suite
from evals.token_utils import (
    TokenLedger,
    count_tokens,
    measure_prompt_payload,
    record_llm_or_context_usage,
)


def test_token_utils_and_ledger() -> None:
    assert count_tokens("") == 0
    assert count_tokens("hello world") > 0
    payload = measure_prompt_payload("system", "context", "query")
    assert payload["total_tokens"] == (
        payload["system_tokens"] + payload["context_tokens"] + payload["query_tokens"]
    )

    ledger = TokenLedger(name="unit_test")
    # 1. Mock fallback (no llm_response)
    entry1 = record_llm_or_context_usage(ledger, "packed context string")
    assert entry1["context_tokens"] == count_tokens("packed context string")
    assert ledger.call_count == 1

    # 2. OpenAI style response.usage
    openai_resp = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=45)
    )
    entry2 = record_llm_or_context_usage(ledger, "packed context string", openai_resp)
    assert entry2["prompt_tokens"] == 120
    assert entry2["completion_tokens"] == 45
    assert ledger.call_count == 2

    # 3. Google GenAI style response.usage_metadata
    genai_resp = SimpleNamespace(
        usage_metadata=SimpleNamespace(prompt_token_count=95, candidates_token_count=30)
    )
    entry3 = record_llm_or_context_usage(ledger, "packed context string", genai_resp)
    assert entry3["prompt_tokens"] == 95
    assert entry3["completion_tokens"] == 30
    assert ledger.call_count == 3


def test_mock_engine_contract() -> None:
    reset_mock_engine()
    ns = "acme/users/emp_042"
    ids = ingest_message(ns, "Our primary database engine is MongoDB.", "user")
    assert len(ids) == 1

    # Valid update at user tier
    ingest_message(ns, "Our primary database engine is Postgres 16.", "user")
    # Contradiction at doc tier (ignored)
    ingest_message(ns, "Our primary database engine is MySQL.", "doc")

    res = recall_context(ns, "What is our primary database engine?", token_budget=800)
    assert res["status"] == "ok"
    assert "Postgres 16" in res["packed_prompt"]
    assert "MySQL" not in res["packed_prompt"]
    assert res["tokens_used"] <= 800

    # Deletion receipt
    ingest_message(ns, "Secret passphrase is OrionVault#2026!", "user")
    del_res = forget_target(ns, "OrionVault#2026!")
    assert del_res["byte_matches"] == 0


def test_live_contract_adapter_pydantic_and_dict() -> None:
    """Verify _wrap_live_contract normalizes both Pydantic BaseModel and dict return types."""

    class FakePydanticRecall:
        def model_dump(self) -> dict:
            return {
                "status": "ok",
                "packed_prompt": "Canonical fact: Postgres 16",
                "citations": ["clm_01"],
                "tokens_used": 6,
                "latency_ms": 1.2,
            }

    class FakePydanticForget:
        def model_dump(self) -> dict:
            return {
                "namespace": "acme/users/emp_042",
                "target": "OrionVault#2026!",
                "byte_matches": 0,
                "verified_clean": True,
            }

    def raw_ingest(namespace: str, text: str, origin: str = "user"):
        return ["clm_01"]

    def raw_recall(namespace: str, query: str, token_budget: int = 800):
        return FakePydanticRecall()

    def raw_forget(namespace: str, target: str):
        return FakePydanticForget()

    ing, rec, fgt = _wrap_live_contract(raw_ingest, raw_recall, raw_forget)
    assert ing("acme/users/emp_042", "hello", "user") == ["clm_01"]
    r_out = rec("acme/users/emp_042", "db?", 800)
    assert r_out["status"] == "ok"
    assert r_out["packed_prompt"] == "Canonical fact: Postgres 16"
    assert r_out["tokens_used"] == 6
    f_out = fgt("acme/users/emp_042", "OrionVault#2026!")
    assert f_out["byte_matches"] == 0


def test_end_to_end_benchmarks() -> None:
    results = run_benchmark_suite(mode="mock")
    assert results["namespace_collision_test"]["isolation_rate_pct"] == 100.0
    assert results["byte_cleanliness"]["knowledge_brain_byte_matches"] == 0
    assert results["token_ledgers"]["collision_ledger"]["call_count"] == 100
    md = evaluate_5_strategies(mode="mock")
    assert "Hybrid Scoped Engine" in md
    assert "Live TokenLedger Accounting Summary" in md
    comparison = run_baseline_comparison(mode="live")
    assert comparison["knowledge_brain"]["byte_clean_deletion_pct"] == 100.0
    assert comparison["mem0_flat_memory_baseline"]["byte_clean_deletion_pct"] == 0.0
    assert mvs_suite is run_benchmark_suite
    summary_json = Path(__file__).resolve().parent.parent / "evals" / "results" / "benchmark_summary.json"
    assert summary_json.exists()
