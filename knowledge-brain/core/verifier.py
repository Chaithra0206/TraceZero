"""Physical zero-byte deletion verification and paraphrase probe tester."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.retrieval import recall_context


def verify_physical_byte_zero(shard_dir: Path, target_val: str) -> Tuple[bool, int, List[str]]:
    """Scan raw binary bytes across all files in shard to assert 0 byte matches.

    Scans:
      - index.sqlite
      - index.sqlite-wal
      - index.sqlite-shm
      - .abstract.md
      - *.okf.md
      - sources/*.txt
    """
    target_bytes = target_val.strip().encode("utf-8")
    target_bytes_lower = target_val.strip().lower().encode("utf-8")

    total_occurrences = 0
    matched_files: List[str] = []

    files_to_scan: List[Path] = []
    # Collect sqlite files
    for name in ["index.sqlite", "index.sqlite-wal", "index.sqlite-shm", ".abstract.md"]:
        p = shard_dir / name
        if p.exists():
            files_to_scan.append(p)

    # Collect okf files
    for p in shard_dir.glob("*.okf.md"):
        files_to_scan.append(p)

    # Collect source files
    sources_dir = shard_dir / "sources"
    if sources_dir.exists():
        for p in sources_dir.glob("*.txt"):
            files_to_scan.append(p)

    for p in files_to_scan:
        try:
            with open(p, "rb") as f:
                content = f.read()
                # Check for raw bytes match (both exact and lowercase)
                count = content.count(target_bytes)
                if target_bytes_lower != target_bytes:
                    count += content.lower().count(target_bytes_lower)

                if count > 0:
                    total_occurrences += count
                    matched_files.append(f"{p.name} ({count} occurrences)")
        except Exception:
            continue

    is_clean = (total_occurrences == 0)
    return is_clean, total_occurrences, matched_files


def run_paraphrase_probes(
    conn: sqlite3.Connection,
    shard_dir: Path,
    namespace: str,
    target_val: str,
    custom_probes: Optional[List[str]] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute paraphrase probe queries to confirm honest abstention on deleted memory."""
    if custom_probes is None:
        probes = [
            f"What is the value of {target_val}?",
            f"Tell me about {target_val}",
            f"Do you remember {target_val}?",
            f"What was decided regarding {target_val}?",
            f"Where did I mention {target_val}?",
            f"What is my preference for {target_val}?",
            f"Can you retrieve details on {target_val}?",
            f"Is {target_val} recorded anywhere in memory?",
            f"What does {target_val} refer to in my settings?",
            f"Give me the source quote for {target_val}",
        ]
    else:
        probes = custom_probes

    results: List[Dict[str, Any]] = []
    all_abstained = True

    for q in probes:
        res = recall_context(conn, shard_dir, namespace, q)
        abstained = (res.status == "abstained") or (target_val.lower() not in res.packed_context.lower())
        if not abstained:
            all_abstained = False
        results.append({
            "probe": q,
            "status": res.status,
            "abstained": abstained,
            "tokens_used": res.tokens_used,
        })

    return all_abstained, results


def verify_deletion(
    conn: sqlite3.Connection,
    shard_dir: Path,
    namespace: str,
    target_val: str,
    probe_queries: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """Combined verification: zero physical byte matches + 100% probe abstention."""
    byte_clean, byte_count, matched_files = verify_physical_byte_zero(shard_dir, target_val)
    probes_clean, probe_results = run_paraphrase_probes(conn, shard_dir, namespace, target_val, probe_queries)

    verified = byte_clean and probes_clean
    details = {
        "target": target_val,
        "byte_clean": byte_clean,
        "byte_occurrences": byte_count,
        "matched_files": matched_files,
        "probes_clean": probes_clean,
        "probe_count": len(probe_results),
        "probe_results": probe_results,
    }
    return verified, details

