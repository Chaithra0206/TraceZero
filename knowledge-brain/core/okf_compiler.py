"""Google OKF v0.2 and OpenViking L0 Compiler."""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Dict, List, Set
import yaml

from core.contracts import PREDICATE_REGISTRY, StorageTier


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compile_okf_files(conn: sqlite3.Connection, shard_dir: Path, namespace: str) -> Dict[str, Path]:
    """Compile active claims into OpenViking Tier L0 (.abstract.md) and Google OKF v0.2 files.

    Generates:
      - .abstract.md (OpenViking L0 ~50-150 tokens core identity & working context)
      - preferences.okf.md
      - decisions.okf.md
      - tasks.okf.md
      - notes.okf.md
    """
    timestamp = now_iso()
    cursor = conn.cursor()

    # Query all active claims with their source file info
    cursor.execute(
        """
        SELECT 
            c.claim_id, c.subject, c.predicate, c.object_val, 
            c.valid_from, c.source_id, c.byte_start, c.byte_end, c.okf_file,
            s.file_path, s.origin, s.trust_tier
        FROM claims_index c
        JOIN sources_index s ON c.source_id = s.source_id
        WHERE c.namespace = ? AND c.status = 'active'
        ORDER BY c.okf_file, c.predicate, c.valid_from ASC
        """,
        (namespace,),
    )
    rows = cursor.fetchall()

    claims_by_file: Dict[str, List[sqlite3.Row]] = {
        "preferences.okf.md": [],
        "decisions.okf.md": [],
        "tasks.okf.md": [],
        "notes.okf.md": [],
    }
    l0_claims: List[sqlite3.Row] = []

    for row in rows:
        target_file = row["okf_file"]
        if target_file not in claims_by_file:
            claims_by_file[target_file] = []
        claims_by_file[target_file].append(row)

        pred_name = row["predicate"]
        meta = PREDICATE_REGISTRY.get(pred_name)
        if meta and meta.storage == StorageTier.PROMPT_L0:
            l0_claims.append(row)

    compiled_paths: Dict[str, Path] = {}

    # 1. Compile OpenViking Tier L0 (.abstract.md)
    abstract_path = shard_dir / ".abstract.md"
    abstract_lines: List[str] = [
        "# Identity & Working Context (OpenViking Tier L0)",
        f"- **Namespace**: {namespace}",
        f"- **Compiled At**: {timestamp}",
        "",
        "## Core Attributes",
    ]
    abstract_sources: Set[str] = set()

    if l0_claims:
        for claim in l0_claims:
            abstract_lines.append(
                f"- **{claim['predicate']}**: {claim['object_val']} [^{claim['source_id']}]"
            )
            abstract_sources.add(
                f"[^{claim['source_id']}]: {claim['file_path']} (bytes {claim['byte_start']}-{claim['byte_end']})"
            )
    else:
        abstract_lines.append("- *(No active L0 identity preferences registered)*")

    if abstract_sources:
        abstract_lines.append("")
        abstract_lines.append("## Provenance")
        for src_line in sorted(abstract_sources):
            abstract_lines.append(src_line)

    abstract_path.write_text("\n".join(abstract_lines) + "\n", encoding="utf-8")
    compiled_paths[".abstract.md"] = abstract_path

    # 2. Compile Google OKF v0.2 Markdown files
    for filename, claims in claims_by_file.items():
        file_path = shard_dir / filename
        source_ids = sorted(list({c["source_id"] for c in claims}))

        # YAML Frontmatter
        frontmatter = {
            "okf_version": "0.2",
            "namespace": namespace,
            "status": "active",
            "updated_at": timestamp,
            "sources": source_ids,
        }
        yaml_str = yaml.dump(frontmatter, sort_keys=False).strip()

        body_lines: List[str] = [f"---", yaml_str, "---", ""]

        if filename == "preferences.okf.md":
            body_lines.append("## User Preferences & Profile")
            if not claims:
                body_lines.append("- *(No active preferences)*")
            for c in claims:
                body_lines.append(
                    f"- **{c['predicate']}**: {c['object_val']} (since {c['valid_from']}) [^{c['source_id']}]"
                )

        elif filename == "decisions.okf.md":
            body_lines.append("## Architectural & Technical Decisions")
            if not claims:
                body_lines.append("- *(No active decisions or constraints)*")
            for c in claims:
                body_lines.append(
                    f"- **{c['predicate']}** [{c['subject']}]: {c['object_val']} (since {c['valid_from']}) [^{c['source_id']}]"
                )

        elif filename == "tasks.okf.md":
            body_lines.append("## Active Tasks & Execution State")
            if not claims:
                body_lines.append("- *(No active task state)*")
            for c in claims:
                if c["predicate"] == "task_completed":
                    body_lines.append(f"- [x] **completed**: {c['object_val']} [^{c['source_id']}]")
                elif c["predicate"] in ("task_pending", "task_goal"):
                    body_lines.append(f"- [ ] **{c['predicate']}**: {c['object_val']} [^{c['source_id']}]")
                else:
                    body_lines.append(f"- **{c['predicate']}**: {c['object_val']} [^{c['source_id']}]")

        elif filename == "notes.okf.md":
            body_lines.append("## Contextual Notes & Observations")
            if not claims:
                body_lines.append("- *(No active notes)*")
            for c in claims:
                body_lines.append(
                    f"- **{c['subject']}** ({c['predicate']}): {c['object_val']} [^{c['source_id']}]"
                )

        # Sources & Lineage footnotes
        body_lines.append("")
        body_lines.append("## Sources & Provenance")
        if claims:
            unique_sources = {
                (c["source_id"], c["file_path"], c["byte_start"], c["byte_end"])
                for c in claims
            }
            for sid, path_str, b_start, b_end in sorted(unique_sources):
                body_lines.append(f"[^{sid}]: {path_str} (bytes {b_start}-{b_end})")
        else:
            body_lines.append("- *(None)*")

        file_path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
        compiled_paths[filename] = file_path

    return compiled_paths

