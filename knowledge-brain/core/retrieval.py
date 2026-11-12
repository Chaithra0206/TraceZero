"""Deterministic query routing, tiered context packing, exact byte spans, and abstention gate."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import sqlite_vec
import tiktoken

from core.contracts import Citation, RetrievalResult
from core.ingest import embed_text


_TIKTOKEN_ENC = None


def get_tokenizer():
    """Return cached tiktoken encoding."""
    global _TIKTOKEN_ENC
    if _TIKTOKEN_ENC is None:
        _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
    return _TIKTOKEN_ENC


def count_tokens(text: str) -> int:
    """Accurately count tokens using cl100k_base."""
    enc = get_tokenizer()
    return len(enc.encode(text))


# Semantic keywords and synonyms for registered predicates
PREDICATE_KEYWORDS: Dict[str, Set[str]] = {
    "employer": {"employer", "company", "work", "works", "working", "job", "office", "organization", "firm", "employ", "employed"},
    "lives_in": {"lives", "live", "living", "reside", "resides", "residing", "location", "city", "place", "based", "home", "country"},
    "favorite_color": {"color", "colour", "shade", "tint", "hue", "favorite_color"},
    "preferred_db": {"db", "database", "storage", "datastore", "postgres", "mysql", "sql", "preferred_db"},
    "role": {"role", "title", "position", "designation", "job", "engineer", "architect", "lead"},
    "coding_style": {"coding", "style", "format", "conventions", "standards", "pep8", "linting"},
    "programming_language": {"language", "python", "typescript", "java", "golang", "rust", "c++"},
    "timezone": {"timezone", "zone", "tz", "utc", "gmt", "ist", "est", "pst"},
    "depends_on": {"depends", "dependency", "dependencies", "depend", "depends_on"},
    "manages": {"manages", "manager", "reports", "lead", "subordinates"},
    "decided": {"decision", "decided", "chose", "chosen", "architecture", "strategy"},
    "constraint": {"constraint", "limit", "restriction", "requirement", "latency", "sla"},
    "task_goal": {"goal", "objective", "task", "milestone", "mission", "target"},
    "task_completed": {"completed", "done", "finished", "resolved"},
    "task_pending": {"pending", "remaining", "next", "todo", "upcoming"},
    "task_status": {"status", "phase", "state", "progress"},
    "has_note": {"note", "notes", "observation", "context", "memo"},
}


def classify_query_route(query: str) -> str:
    """Deterministic 0-LLM-token query router.

    Routes:
      - SQL_AGGREGATE: counting, aggregations, task tallies
      - GRAPH_CTE: multi-hop dependencies, hierarchy, management relations
      - TEMPORAL_HISTORY: changes, historical states, previous values
      - HYBRID_TIERED: preferences, facts, general semantic lookup
    """
    q = query.lower()

    # Temporal history queries
    if any(k in q for k in [
        "what changed", "history", "previously", "former", "timeline",
        "past", "used to", "before", "prior", "superseded", "historical"
    ]):
        return "TEMPORAL_HISTORY"

    # Graph / CTE queries
    if any(k in q for k in [
        "depends on", "dependency", "dependencies", "manages", "managed by",
        "hierarchy", "lineage", "chain", "path", "subordinates", "reports to"
    ]):
        return "GRAPH_CTE"

    # Aggregates / counts
    if any(k in q for k in [
        "how many", "count", "number of", "total", "sum", "average",
        "aggregate", "list all tasks", "pending tasks count", "tally"
    ]):
        return "SQL_AGGREGATE"

    return "HYBRID_TIERED"


def read_exact_byte_span(shard_dir: Path, rel_path: str, byte_start: int, byte_end: int) -> str:
    """Perform binary seek and read exact byte span from disk.

    Skips any spans containing [REDACTED to guarantee deleted memory is never exposed.
    """
    file_path = shard_dir / rel_path
    if not file_path.exists():
        return ""

    if byte_end <= byte_start:
        return ""

    try:
        with open(file_path, "rb") as f:
            f.seek(byte_start)
            raw_bytes = f.read(byte_end - byte_start)
            text = raw_bytes.decode("utf-8", errors="replace")
            if "[REDACTED" in text:
                return ""
            return text
    except Exception:
        return ""


def recall_context(
    conn: sqlite3.Connection,
    shard_dir: Path,
    namespace: str,
    query: str,
    token_budget: int = 800,
) -> RetrievalResult:
    """Recall scoped memory context adhering strictly to token budget and abstention gate."""
    route = classify_query_route(query)
    enc = get_tokenizer()
    cursor = conn.cursor()

    # Step 1: Semantic plane search (sqlite-vec)
    query_emb_blob = embed_text(query)
    vec_matches: List[Tuple[int, float]] = []
    try:
        cursor.execute(
            """
            SELECT rowid, distance 
            FROM vec_claims 
            WHERE embedding MATCH ? AND k = 10 
            ORDER BY distance ASC
            """,
            (query_emb_blob,),
        )
        vec_matches = [(row[0], row[1]) for row in cursor.fetchall()]
    except Exception:
        vec_matches = []

    best_vec_dist = min([dist for _, dist in vec_matches]) if vec_matches else 999.0

    # Step 2: Check for exact match on known entity or registered predicate
    cursor.execute(
        "SELECT DISTINCT predicate, subject FROM claims_index WHERE namespace = ? AND status = 'active'",
        (namespace,),
    )
    active_rows = cursor.fetchall()
    active_predicates = [r["predicate"] for r in active_rows]
    q_words = set(re.findall(r"\w+", query.lower()))
    has_exact_predicate_match = False
    matching_active_predicates: List[str] = []

    for pred in active_predicates:
        pred_lower = pred.lower()
        kw_set = PREDICATE_KEYWORDS.get(pred_lower, set())
        pred_parts = pred_lower.split("_")
        if pred_lower in q_words or pred_parts[-1] in q_words or bool(q_words & kw_set):
            has_exact_predicate_match = True
            matching_active_predicates.append(pred)

    # Step 3: Strict Abstention Gate
    # If no keyword/predicate match on active domain knowledge AND best sqlite-vec distance > 0.80 -> Abstain!
    if not has_exact_predicate_match and best_vec_dist > 0.80:
        return RetrievalResult(
            status="abstained",
            route=route,
            claims=[],
            citations=[],
            packed_context="I have no memory of that.",
            tokens_used=0,
        )

    # Step 4: Route-specific claim gathering
    matched_claims: List[Dict[str, Any]] = []
    citations: List[Citation] = []

    if route == "TEMPORAL_HISTORY":
        cursor.execute(
            """
            SELECT c.*, s.file_path, s.origin, s.trust_tier
            FROM claims_index c
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.status IN ('active', 'superseded')
            ORDER BY c.valid_from ASC
            """,
            (namespace,),
        )
        for r in cursor.fetchall():
            matched_claims.append(dict(r))

    elif route == "GRAPH_CTE":
        cursor.execute(
            """
            WITH RECURSIVE graph_chain(subject, predicate, object_val, depth) AS (
                SELECT subject, predicate, object_val, 1
                FROM claims_index
                WHERE namespace = ? AND status = 'active' AND predicate IN ('depends_on', 'manages')
                UNION ALL
                SELECT c.subject, c.predicate, c.object_val, gc.depth + 1
                FROM claims_index c
                JOIN graph_chain gc ON c.subject = gc.object_val
                WHERE c.namespace = ? AND c.status = 'active' AND c.predicate IN ('depends_on', 'manages')
                AND gc.depth < 5
            )
            SELECT DISTINCT gc.subject, gc.predicate, gc.object_val, c.claim_id, c.status, c.valid_from, 
                            c.source_id, c.byte_start, c.byte_end, s.file_path, s.origin, s.trust_tier
            FROM graph_chain gc
            JOIN claims_index c ON gc.subject = c.subject AND gc.predicate = c.predicate AND gc.object_val = c.object_val
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.status = 'active'
            """,
            (namespace, namespace, namespace),
        )
        for r in cursor.fetchall():
            matched_claims.append(dict(r))

    elif route == "SQL_AGGREGATE":
        cursor.execute(
            """
            SELECT c.*, s.file_path, s.origin, s.trust_tier
            FROM claims_index c
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.status = 'active'
            ORDER BY c.predicate, c.valid_from DESC
            """,
            (namespace,),
        )
        for r in cursor.fetchall():
            matched_claims.append(dict(r))

    else:
        # HYBRID_TIERED: retrieve claims via vector and FTS matches
        candidate_claim_ids = set()

        # From vec matches (distance <= 0.80)
        vec_rowids = [r_id for r_id, dist in vec_matches if dist <= 0.80]
        if vec_rowids:
            placeholders = ",".join("?" for _ in vec_rowids)
            cursor.execute(
                f"SELECT claim_id FROM lineage_index WHERE vec_rowid IN ({placeholders})",
                vec_rowids,
            )
            for r in cursor.fetchall():
                candidate_claim_ids.add(r[0])

        # From predicate keyword match if vec alone didn't capture
        if matching_active_predicates:
            for pred in matching_active_predicates:
                cursor.execute(
                    "SELECT claim_id FROM claims_index WHERE namespace = ? AND predicate = ? AND status = 'active'",
                    (namespace, pred),
                )
                for r in cursor.fetchall():
                    candidate_claim_ids.add(r[0])

        if candidate_claim_ids:
            placeholders = ",".join("?" for _ in candidate_claim_ids)
            cursor.execute(
                f"""
                SELECT c.*, s.file_path, s.origin, s.trust_tier
                FROM claims_index c
                JOIN sources_index s ON c.source_id = s.source_id
                WHERE c.namespace = ? AND c.status = 'active' AND c.claim_id IN ({placeholders})
                ORDER BY c.valid_from DESC
                """,
                [namespace] + list(candidate_claim_ids),
            )
            for r in cursor.fetchall():
                matched_claims.append(dict(r))

    # If route failed to find any active claims
    if not matched_claims:
        return RetrievalResult(
            status="abstained",
            route=route,
            claims=[],
            citations=[],
            packed_context="I have no memory of that.",
            tokens_used=0,
        )

    # Step 5: Tiered Context Packing within token_budget
    l0_content = ""
    abstract_file = shard_dir / ".abstract.md"
    if abstract_file.exists():
        l0_content = abstract_file.read_text(encoding="utf-8").strip()

    context_sections: List[str] = [f"# Retrieved Knowledge Context (Route: {route})"]
    if l0_content:
        context_sections.append(f"## OpenViking Tier L0 (Core Identity)\n{l0_content}")

    # L1 Triples
    l1_lines: List[str] = ["## Tier L1 Active Triples"]
    for c in matched_claims:
        status_val = c.get("status", "active")
        status_suffix = f" [status={status_val}]" if status_val != "active" else ""
        l1_lines.append(
            f"- **{c['subject']}** -> **{c['predicate']}**: {c['object_val']} (since {c['valid_from']}){status_suffix} [^{c['source_id']}]"
        )
    context_sections.append("\n".join(l1_lines))

    # L2 Exact byte spans
    l2_lines: List[str] = ["## Tier L2 Exact Quotes & Provenance"]
    seen_sources = set()
    for c in matched_claims:
        span_text = read_exact_byte_span(shard_dir, c["file_path"], c["byte_start"], c["byte_end"])
        if span_text and c["source_id"] not in seen_sources:
            seen_sources.add(c["source_id"])
            l2_lines.append(
                f"[^{c['source_id']}]: \"{span_text}\" ({c['file_path']} bytes {c['byte_start']}-{c['byte_end']})"
            )
            citations.append(
                Citation(
                    source_id=c["source_id"],
                    file_path=c["file_path"],
                    byte_start=c["byte_start"],
                    byte_end=c["byte_end"],
                    exact_quote=span_text,
                )
            )

    if len(l2_lines) > 1:
        context_sections.append("\n".join(l2_lines))

    raw_packed = "\n\n".join(context_sections)

    # Step 6: Hard Token Budget Ceiling Enforcement
    raw_tokens = enc.encode(raw_packed)
    if len(raw_tokens) > token_budget:
        truncated_tokens = raw_tokens[:token_budget]
        packed_context = enc.decode(truncated_tokens)
    else:
        packed_context = raw_packed

    tokens_used = len(enc.encode(packed_context))

    return RetrievalResult(
        status="ok",
        route=route,
        claims=matched_claims,
        citations=citations,
        packed_context=packed_context,
        tokens_used=tokens_used,
    )
