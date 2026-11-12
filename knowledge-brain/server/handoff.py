"""Cross-agent handoff protocol using Google OKF v0.2 tasks.okf.md and MemoryStore."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import yaml

from core.contracts import ClaimRecord, ClaimStatus, HandoffPacket
from core.retrieval import count_tokens, get_tokenizer
from core.storage_api import MemoryStore


def handoff_create(
    store: MemoryStore,
    namespace: str,
    task_id: str,
    goal: str,
    completed_steps: List[str],
    pending_steps: List[str],
    open_questions: Optional[List[str]] = None,
    relied_on_claim_ids: Optional[List[str]] = None,
    agent_id: str = "agent_a_claude",
) -> HandoffPacket:
    """Write portable Google OKF v0.2 tasks.okf.md with verified decisions and provenance."""
    shard_dir = store.sm.get_shard_dir(namespace)
    now = datetime.now(timezone.utc).isoformat()
    questions = open_questions or []
    requested_ids = relied_on_claim_ids or []

    with store.sm.get_connection(namespace) as conn:
        if requested_ids:
            placeholders = ",".join("?" for _ in requested_ids)
            rows = conn.execute(
                f"""SELECT c.*, s.file_path, s.origin, s.trust_tier
                    FROM claims_index c
                    JOIN sources_index s ON c.source_id = s.source_id
                    WHERE c.claim_id IN ({placeholders}) AND c.status = 'active'
                    ORDER BY c.valid_from ASC""",
                requested_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.*, s.file_path, s.origin, s.trust_tier
                   FROM claims_index c
                   JOIN sources_index s ON c.source_id = s.source_id
                   WHERE c.namespace = ? AND c.status = 'active'
                   ORDER BY c.valid_from ASC""",
                (namespace,),
            ).fetchall()

    resolved_claim_ids: List[str] = []
    sources_meta: Dict[str, Dict[str, Any]] = {}
    verified_decisions: List[Dict[str, Any]] = []
    claim_records: List[ClaimRecord] = []
    citations: List[str] = []

    for r in rows:
        cid = r["claim_id"]
        sid = r["source_id"]
        resolved_claim_ids.append(cid)
        cite_tag = f"[^{sid}]"
        if cite_tag not in citations:
            citations.append(cite_tag)

        sources_meta[sid] = {
            "id": sid,
            "path": r["file_path"],
            "span": f"{r['byte_start']}:{r['byte_end']}",
            "origin": r["origin"],
            "trust_tier": r["trust_tier"],
        }

        quote = store.read_verified_span(
            namespace, r["file_path"], r["byte_start"], r["byte_end"]
        )
        verified_decisions.append(
            {
                "claim_id": cid,
                "subject": r["subject"],
                "predicate": r["predicate"],
                "object_val": r["object_val"],
                "source_id": sid,
                "citation": cite_tag,
                "exact_quote": quote,
            }
        )
        claim_records.append(
            ClaimRecord(
                claim_id=cid,
                namespace=r["namespace"],
                subject=r["subject"],
                predicate=r["predicate"],
                object_val=r["object_val"],
                status=ClaimStatus(r["status"]),
                valid_from=r["valid_from"],
                valid_to=r["valid_to"],
                source_id=sid,
                byte_start=r["byte_start"],
                byte_end=r["byte_end"],
                okf_file=r["okf_file"],
            )
        )

    frontmatter = {
        "okf_version": "0.2",
        "namespace": f"viking://{namespace.strip('/')}/tasks.okf.md",
        "task_id": task_id,
        "created_by_agent": agent_id,
        "status": "in_progress",
        "updated_at": now,
        "relied_on_claims": resolved_claim_ids,
        "sources": list(sources_meta.values()),
    }

    lines: List[str] = [
        "---",
        yaml.safe_dump(frontmatter, sort_keys=False).strip(),
        "---",
        "",
        "## Goal",
        goal,
        "",
        "## Completed Steps",
    ]
    if completed_steps:
        for s in completed_steps:
            lines.append(f"- [x] {s}")
    else:
        lines.append("- *(None)*")

    lines.extend(["", "## Pending Steps"])
    if pending_steps:
        for s in pending_steps:
            lines.append(f"- [ ] {s}")
    else:
        lines.append("- *(None)*")

    lines.extend(["", "## Verified Decisions & Provenance"])
    if verified_decisions:
        for d in verified_decisions:
            lines.append(
                f"- **{d['subject']}.{d['predicate']}**: {d['object_val']} {d['citation']}"
            )
    else:
        lines.append("- *(None)*")

    lines.extend(["", "## Open Questions"])
    if questions:
        for q in questions:
            lines.append(f"- {q}")
    else:
        lines.append("- *(None)*")

    okf_path = shard_dir / "tasks.okf.md"
    full_markdown = "\n".join(lines) + "\n"
    okf_path.write_text(full_markdown, encoding="utf-8")

    tokens_used = count_tokens(full_markdown)

    return HandoffPacket(
        packet_id=f"hnd_{uuid.uuid4().hex[:8]}",
        source_agent=agent_id,
        target_agent="agent_b",
        namespace=namespace,
        task_id=task_id,
        goal=goal,
        completed_steps=completed_steps,
        pending_steps=pending_steps,
        open_questions=questions,
        relied_on_claim_ids=resolved_claim_ids,
        verified_decisions=verified_decisions,
        citations=citations,
        source_okf_path=str(okf_path),
        claims=claim_records,
        packed_prompt=full_markdown,
        tokens_used=tokens_used,
        timestamp=now,
        context_summary=goal,
    )


def handoff_get(
    store: MemoryStore, namespace: str, task_id: Optional[str] = None
) -> Dict[str, Any]:
    """Read tasks.okf.md from disk and resolve live provenance quotes (<350 tokens)."""
    shard_dir = store.sm.get_shard_dir(namespace)
    okf_path = shard_dir / "tasks.okf.md"
    if not okf_path.exists():
        return {
            "status": "not_found",
            "namespace": namespace,
            "task_id": task_id or "",
            "goal": "",
            "completed_steps": [],
            "pending_steps": [],
            "open_questions": [],
            "relied_on_claims": [],
            "active_decisions": [],
            "citations": [],
            "packed_prompt": "",
            "tokens_used": 0,
        }

    raw_text = okf_path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_text, re.DOTALL)
    frontmatter: Dict[str, Any] = {}
    body = raw_text
    if fm_match:
        frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        body = fm_match.group(2)

    parsed_task_id = frontmatter.get("task_id", task_id or "")
    created_by_agent = frontmatter.get("created_by_agent", "agent_a_claude")
    updated_at = frontmatter.get("updated_at", "")
    relied_on_claims: List[str] = frontmatter.get("relied_on_claims", [])

    goal_lines: List[str] = []
    completed_steps: List[str] = []
    pending_steps: List[str] = []
    open_questions: List[str] = []

    current_section = ""
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("## Goal"):
            current_section = "goal"
            continue
        elif s.startswith("## Completed Steps"):
            current_section = "completed"
            continue
        elif s.startswith("## Pending Steps"):
            current_section = "pending"
            continue
        elif s.startswith("## Verified Decisions"):
            current_section = "decisions"
            continue
        elif s.startswith("## Open Questions"):
            current_section = "questions"
            continue
        elif s.startswith("## "):
            current_section = ""
            continue

        if not s or s.startswith("- *(None)*"):
            continue

        if current_section == "goal":
            goal_lines.append(s)
        elif current_section == "completed" and s.startswith("- [x]"):
            completed_steps.append(s[5:].strip())
        elif current_section == "pending" and s.startswith("- [ ]"):
            pending_steps.append(s[5:].strip())
        elif current_section == "questions" and s.startswith("- "):
            open_questions.append(s[2:].strip())

    goal = " ".join(goal_lines).strip()

    # Resolve live provenance quotes for relied_on_claims via store.explain_claim
    active_decisions: List[Dict[str, Any]] = []
    citations: List[str] = []
    for cid in relied_on_claims:
        explained = store.explain_claim(namespace, cid)
        if explained and explained.get("status") == ClaimStatus.ACTIVE.value:
            cite_tag = f"[^{explained['source_id']}]"
            if cite_tag not in citations:
                citations.append(cite_tag)
            active_decisions.append(
                {
                    "claim_id": cid,
                    "subject": explained["subject"],
                    "predicate": explained["predicate"],
                    "object_val": explained["object_val"],
                    "source_id": explained["source_id"],
                    "citation": cite_tag,
                    "exact_quote": explained.get("exact_quote", ""),
                }
            )

    # Build compact Agent B handoff prompt (<350 tokens)
    compact_lines: List[str] = [
        f"# Handoff Brief ({parsed_task_id})",
        f"Goal: {goal}",
        "Completed: " + ("; ".join(completed_steps) if completed_steps else "None"),
        "Pending: " + ("; ".join(pending_steps) if pending_steps else "None"),
        "Decisions:",
    ]
    for d in active_decisions:
        compact_lines.append(
            f"- {d['predicate']}: {d['object_val']} {d['citation']} (\"{d['exact_quote']}\")"
        )
    if open_questions:
        compact_lines.append("Open Questions: " + "; ".join(open_questions))

    packed_prompt = "\n".join(compact_lines)
    enc = get_tokenizer()
    raw_tokens = enc.encode(packed_prompt)
    if len(raw_tokens) > 340:
        packed_prompt = enc.decode(raw_tokens[:340])
    tokens_used = len(enc.encode(packed_prompt))

    return {
        "status": "ok",
        "task_id": parsed_task_id,
        "namespace": namespace,
        "created_by_agent": created_by_agent,
        "updated_at": updated_at,
        "goal": goal,
        "completed_steps": completed_steps,
        "pending_steps": pending_steps,
        "open_questions": open_questions,
        "relied_on_claims": relied_on_claims,
        "active_decisions": active_decisions,
        "citations": citations,
        "packed_prompt": packed_prompt,
        "tokens_used": tokens_used,
    }
