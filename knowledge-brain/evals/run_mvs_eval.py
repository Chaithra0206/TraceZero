"""Multi-Valued Schema (MVS) and Multi-Shard scaling evaluation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from core.ingest import ingest_message
from core.retrieval import recall_context
from core.schema import get_shard


def evaluate_mvs_scaling(memory_root: Path, num_shards: int = 25) -> Dict[str, Any]:
    """Test retrieval speed and isolation across multiple independent shards."""
    colors = [
        "navy blue", "crimson", "forest green", "amber", "teal",
        "indigo", "violet", "slate gray", "emerald", "coral",
        "cyan", "magenta", "maroon", "olive", "turquoise",
        "sapphire", "ruby", "lavender", "charcoal", "ochre",
        "platinum", "bronze", "copper", "pearl", "obsidian",
    ]

    # Seed isolated shards
    for i in range(num_shards):
        ns = f"acme/users/emp_{i:03d}"
        color = colors[i % len(colors)]
        conn, shard_dir = get_shard(memory_root, ns)
        ingest_message(
            conn=conn,
            shard_dir=shard_dir,
            namespace=ns,
            raw_text=f"Hello, my favorite color is {color}.",
            session_id="init_pref",
            origin="user",
        )
        conn.close()

    # Benchmark retrieval latency for targeted shard emp_042 (or emp_000 up to num_shards)
    target_idx = 42 if num_shards > 42 else (num_shards - 1)
    target_ns = f"acme/users/emp_{target_idx:03d}"
    expected_color = colors[target_idx % len(colors)]

    conn, shard_dir = get_shard(memory_root, target_ns)

    t0 = time.perf_counter()
    res = recall_context(conn, shard_dir, target_ns, "What is my favorite color?", token_budget=400)
    lat_ms = (time.perf_counter() - t0) * 1000.0

    conn.close()

    correct_color_found = expected_color.lower() in res.packed_context.lower()
    # Ensure no other color leaked into the context
    no_leakage = True
    for idx, c in enumerate(colors):
        if idx != (target_idx % len(colors)) and c.lower() in res.packed_context.lower():
            no_leakage = False
            break

    return {
        "num_shards": num_shards,
        "target_namespace": target_ns,
        "expected_color": expected_color,
        "latency_ms": lat_ms,
        "correct_color_found": correct_color_found,
        "no_leakage": no_leakage,
    }


if __name__ == "__main__":
    import tempfile
    from core.schema import close_all_shards
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        res = evaluate_mvs_scaling(Path(tmpdir), num_shards=25)
        close_all_shards()
        print(f"MVS Evaluation across {res['num_shards']} shards:")
        print(f"  - Target Shard: {res['target_namespace']}")
        print(f"  - Latency:      {res['latency_ms']:.2f}ms (Threshold < 20ms)")
        print(f"  - Accuracy:     {res['correct_color_found']}")
        print(f"  - Isolation:    {res['no_leakage']}")
