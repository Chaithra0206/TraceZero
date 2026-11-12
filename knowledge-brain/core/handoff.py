"""Cross-agent handoff management via Google OKF v0.2 tasks file."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from core.contracts import HandoffPacket
from core.okf_compiler import now_iso


def handoff_create(
    conn: Optional[sqlite3.Connection],
    shard_dir: Path,
    namespace: str,
    task_goal: str,
    completed_steps: List[str],
    pending_steps: List[str],
    blocked_steps: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    decisions: Optional[Dict[str, str]] = None,
) -> HandoffPacket:
    """Create or update tasks.okf.md so another agent can immediately resume mid-flight."""
    timestamp = now_iso()
    blocked = blocked_steps or []
    consts = constraints or []
    decs = decisions or {}

    frontmatter = {
        "okf_version": "0.2",
        "namespace": namespace,
        "status": "in_progress",
        "task_goal": task_goal,
        "updated_at": timestamp,
        "sources": ["handoff_checkpoint"],
    }
    yaml_header = yaml.dump(frontmatter, sort_keys=False).strip()

    body_lines: List[str] = [
        "---",
        yaml_header,
        "---",
        "",
        "# Cross-Agent Handoff Execution State",
        f"**Task Goal**: {task_goal}",
        "",
        "## Completed Steps",
    ]
    if completed_steps:
        for s in completed_steps:
            body_lines.append(f"- [x] {s}")
    else:
        body_lines.append("- *(None)*")

    body_lines.append("")
    body_lines.append("## Pending Steps")
    if pending_steps:
        for s in pending_steps:
            body_lines.append(f"- [ ] {s}")
    else:
        body_lines.append("- *(None)*")

    if blocked:
        body_lines.append("")
        body_lines.append("## Blocked Steps")
        for s in blocked:
            body_lines.append(f"- [-] {s}")

    if consts:
        body_lines.append("")
        body_lines.append("## Guardrails & Constraints")
        for c in consts:
            body_lines.append(f"- {c}")

    if decs:
        body_lines.append("")
        body_lines.append("## Active Architectural Decisions")
        for k, v in decs.items():
            body_lines.append(f"- **{k}**: {v}")

    body_lines.append("")
    body_lines.append("## Provenance")
    body_lines.append(f"[^handoff_checkpoint]: tasks.okf.md created at {timestamp}")

    target_path = shard_dir / "tasks.okf.md"
    target_path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")

    return HandoffPacket(
        namespace=namespace,
        task_goal=task_goal,
        completed_steps=completed_steps,
        pending_steps=pending_steps,
        blocked_steps=blocked,
        constraints=consts,
        active_decisions=decs,
        source_okf_path=str(target_path),
        timestamp=timestamp,
    )


def handoff_get(shard_dir: Path, namespace: str) -> HandoffPacket:
    """Read and parse tasks.okf.md to restore state for Agent 2 without raw chat history."""
    tasks_file = shard_dir / "tasks.okf.md"
    if not tasks_file.exists():
        return HandoffPacket(
            namespace=namespace,
            task_goal="Unknown",
            completed_steps=[],
            pending_steps=[],
            blocked_steps=[],
            constraints=[],
            active_decisions={},
            source_okf_path=str(tasks_file),
            timestamp=now_iso(),
        )

    content = tasks_file.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    task_goal = "General Execution"
    timestamp = now_iso()
    body = content

    if fm_match:
        yaml_content = fm_match.group(1)
        body = fm_match.group(2)
        try:
            parsed_fm = yaml.safe_load(yaml_content) or {}
            task_goal = parsed_fm.get("task_goal", task_goal)
            timestamp = parsed_fm.get("updated_at", timestamp)
        except Exception:
            pass

    completed_steps: List[str] = []
    pending_steps: List[str] = []
    blocked_steps: List[str] = []
    constraints: List[str] = []
    decisions: Dict[str, str] = {}

    current_section = ""
    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith("## Completed"):
            current_section = "completed"
            continue
        elif line_s.startswith("## Pending"):
            current_section = "pending"
            continue
        elif line_s.startswith("## Blocked"):
            current_section = "blocked"
            continue
        elif line_s.startswith("## Guardrails") or line_s.startswith("## Constraints"):
            current_section = "constraints"
            continue
        elif line_s.startswith("## Active Architectural Decisions") or line_s.startswith("## Decisions"):
            current_section = "decisions"
            continue
        elif line_s.startswith("##"):
            current_section = ""
            continue

        if not line_s or line_s.startswith("#") or line_s.startswith("- *("):
            continue

        if current_section == "completed" and line_s.startswith("- [x]"):
            completed_steps.append(line_s[5:].strip())
        elif current_section == "pending" and line_s.startswith("- [ ]"):
            pending_steps.append(line_s[5:].strip())
        elif current_section == "blocked" and line_s.startswith("- [-]"):
            blocked_steps.append(line_s[5:].strip())
        elif current_section == "constraints" and line_s.startswith("-"):
            constraints.append(line_s[1:].strip())
        elif current_section == "decisions" and line_s.startswith("- **"):
            m = re.match(r"-\s*\*\*([^*]+)\*\*:\s*(.*)", line_s)
            if m:
                decisions[m.group(1).strip()] = m.group(2).strip()

    return HandoffPacket(
        namespace=namespace,
        task_goal=task_goal,
        completed_steps=completed_steps,
        pending_steps=pending_steps,
        blocked_steps=blocked_steps,
        constraints=constraints,
        active_decisions=decisions,
        source_okf_path=str(tasks_file),
        timestamp=timestamp,
    )

