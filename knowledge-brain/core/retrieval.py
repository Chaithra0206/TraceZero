"""Deterministic query routing, tiered context packing, exact byte spans, and abstention gate."""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set

import tiktoken

from core.contracts import Citation, ClaimRecord, ClaimStatus, RetrievalResult
from core.storage_api import MemoryStore

_TIKTOKEN_ENC = None


def get_tokenizer():
    """Return cached tiktoken encoding."""
    global _TIKTOKEN_ENC
    if _TIKTOKEN_ENC is None:
        _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
    return _TIKTOKEN_ENC


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base."""
    return len(get_tokenizer().encode(text))


PREDICATE_KEYWORDS: Dict[str, Set[str]] = {
    "employer": {"employer", "company", "work", "works", "working", "job", "office", "organization", "firm", "employ", "employed"},
    "lives_in": {"lives", "live", "living", "reside", "resides", "residing", "location", "city", "place", "based", "home", "country", "moved", "relocated"},
    "favorite_color": {"color", "colour", "shade", "tint", "hue", "favorite_color"},
    "primary_language": {"primary_language", "programming", "language", "rust", "python"},
    "assigned_team": {"team", "assigned_team", "squad", "group"},
    "preferred_db": {"db", "database", "engine", "storage", "datastore", "postgres", "postgresql", "mysql", "mongodb", "preferred_db"},
    "aws_region": {"aws", "region", "regions", "aws_region", "oregon"},
    "deployment_env": {"deployment_env", "deployment", "environment", "canary"},
    "vault_passphrase": {"vault", "passphrase", "credential", "password", "break-glass", "orionvault"},
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
    "task_pending": {"pending", "remaining", "todo", "upcoming"},
    "task_status": {"status", "phase", "state", "progress"},
    "has_note": {"note", "notes", "observation", "context", "memo"},
}


def classify_query_route(query: str) -> str:
    """Deterministic 0-LLM-token query router."""
    q = query.lower()

    if any(k in q for k in [
        "what changed", "history", "previously", "former", "timeline",
        "past", "used to", "before", "prior", "superseded", "historical",
    ]):
        return "TEMPORAL_HISTORY"

    if any(k in q for k in [
        "depends on", "dependency", "dependencies", "manages", "managed by",
        "hierarchy", "lineage", "chain", "path", "subordinates", "reports to",
    ]):
        return "GRAPH_CTE"

    if any(k in q for k in [
        "how many", "count", "number of", "total", "sum", "average",
        "aggregate", "list all tasks", "pending tasks count", "tally",
    ]):
        return "SQL_AGGREGATE"

    return "HYBRID_TIERED"


def _row_to_claim_record(r: Dict[str, Any], namespace: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=r["claim_id"],
        namespace=r.get("namespace", namespace),
        subject=r["subject"],
        predicate=r["predicate"],
        object_val=r["object_val"],
        status=ClaimStatus(r.get("status", "active")),
        valid_from=r["valid_from"],
        valid_to=r.get("valid_to"),
        source_id=r["source_id"],
        byte_start=r["byte_start"],
        byte_end=r["byte_end"],
        okf_file=r.get("okf_file", "preferences.okf.md"),
    )


def recall_context(
    store: MemoryStore,
    namespace: str,
    query: str,
    token_budget: int = 800,
) -> RetrievalResult:
    """Recall scoped memory via MemoryStore adhering to token budget and abstention gate."""
    t0 = time.perf_counter()
    route = classify_query_route(query)
    enc = get_tokenizer()

    # Step 1: Semantic search via MemoryStore
    vec_hits = store.search_hybrid(
        namespace=namespace,
        query=query,
        top_k=10,
        include_superseded=(route == "TEMPORAL_HISTORY"),
    )
    active_vec_hits = [
        h for h in vec_hits
        if (route == "TEMPORAL_HISTORY" or h.get("status") == "active")
    ]
    best_vec_dist = min((h["distance"] for h in active_vec_hits), default=999.0)

    # Step 2: Check active predicates in namespace for deterministic keyword matching
    with store.sm.get_connection(namespace) as conn:
        active_pred_rows = conn.execute(
            "SELECT DISTINCT predicate FROM claims_index WHERE namespace = ? AND status = 'active'",
            (namespace,),
        ).fetchall()
    active_predicates = [r["predicate"] for r in active_pred_rows]

    q_words = set(re.findall(r"\w+", query.lower())) | set(
        re.findall(r"[a-z0-9_#-]+", query.lower())
    )
    matching_active_predicates: List[str] = []
    for pred in active_predicates:
        pred_lower = pred.lower()
        kw_set = PREDICATE_KEYWORDS.get(pred_lower, set())
        pred_parts = pred_lower.split("_")
        if pred_lower in q_words or pred_parts[-1] in q_words or bool(q_words & kw_set):
            matching_active_predicates.append(pred)

    has_exact_predicate_match = len(matching_active_predicates) > 0

    # Filter semantic hits against the 0.65 cosine similarity gate (L2 <= 0.837 for
    # structured claims; tighter <= 0.68 for noisy uncategorized 'has_note' logs).
    qualifying_vec_hits = [
        h for h in active_vec_hits
        if (h["distance"] <= 0.68 if h.get("predicate") == "has_note" else h["distance"] <= 0.84)
    ]

    # Step 3: Strict Abstention Gate
    if not has_exact_predicate_match and not qualifying_vec_hits:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return RetrievalResult(
            status="abstained",
            route=route,
            packed_prompt="I have no memory of that.",
            claims=[],
            citations=[],
            tokens_used=0,
            latency_ms=latency_ms,
        )

    # Step 4: Route-specific claim gathering
    matched_rows: List[Dict[str, Any]] = []
    seen_claim_ids: Set[str] = set()

    def _add_row(row_dict: Dict[str, Any]):
        cid = row_dict["claim_id"]
        if cid not in seen_claim_ids:
            seen_claim_ids.add(cid)
            matched_rows.append(row_dict)

    if route == "TEMPORAL_HISTORY":
        with store.sm.get_connection(namespace) as conn:
            if matching_active_predicates:
                placeholders = ",".join("?" for _ in matching_active_predicates)
                rows = conn.execute(
                    f"""SELECT c.*, s.file_path, s.origin, s.trust_tier
                        FROM claims_index c
                        JOIN sources_index s ON c.source_id = s.source_id
                        WHERE c.namespace = ? AND c.status IN ('active', 'superseded')
                          AND c.predicate IN ({placeholders})
                        ORDER BY c.valid_from ASC""",
                    [namespace, *matching_active_predicates],
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT c.*, s.file_path, s.origin, s.trust_tier
                       FROM claims_index c
                       JOIN sources_index s ON c.source_id = s.source_id
                       WHERE c.namespace = ? AND c.status IN ('active', 'superseded')
                         AND c.predicate != 'has_note'
                       ORDER BY c.valid_from ASC""",
                    (namespace,),
                ).fetchall()
        for r in rows:
            _add_row(dict(r))

    elif route == "GRAPH_CTE":
        # Find candidate root subjects from query words or existing active subjects
        with store.sm.get_connection(namespace) as conn:
            subj_rows = conn.execute(
                "SELECT DISTINCT subject FROM claims_index WHERE namespace = ? AND status = 'active'",
                (namespace,),
            ).fetchall()
        candidate_roots = [
            r["subject"] for r in subj_rows if r["subject"].lower() in q_words
        ]
        if not candidate_roots and subj_rows:
            candidate_roots = [r["subject"] for r in subj_rows[:3]]

        for root in candidate_roots:
            hops = store.query_graph_multihop(namespace, root, max_hops=5)
            if hops:
                hop_ids = [h["claim_id"] for h in hops]
                placeholders = ",".join("?" for _ in hop_ids)
                with store.sm.get_connection(namespace) as conn:
                    full_rows = conn.execute(
                        f"""SELECT c.*, s.file_path, s.origin, s.trust_tier
                            FROM claims_index c
                            JOIN sources_index s ON c.source_id = s.source_id
                            WHERE c.claim_id IN ({placeholders})""",
                        hop_ids,
                    ).fetchall()
                for r in full_rows:
                    _add_row(dict(r))

    elif route == "SQL_AGGREGATE":
        with store.sm.get_connection(namespace) as conn:
            if matching_active_predicates:
                placeholders = ",".join("?" for _ in matching_active_predicates)
                rows = conn.execute(
                    f"""SELECT c.*, s.file_path, s.origin, s.trust_tier
                        FROM claims_index c
                        JOIN sources_index s ON c.source_id = s.source_id
                        WHERE c.namespace = ? AND c.status = 'active'
                          AND c.predicate IN ({placeholders})
                        ORDER BY c.predicate, c.valid_from DESC""",
                    [namespace, *matching_active_predicates],
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT c.*, s.file_path, s.origin, s.trust_tier
                       FROM claims_index c
                       JOIN sources_index s ON c.source_id = s.source_id
                       WHERE c.namespace = ? AND c.status = 'active'
                         AND c.predicate != 'has_note'
                       ORDER BY c.predicate, c.valid_from DESC""",
                    (namespace,),
                ).fetchall()
        for r in rows:
            _add_row(dict(r))

    else:
        # HYBRID_TIERED: prioritize specific active predicates over stated/has_note fallback, newest first
        if matching_active_predicates:
            placeholders = ",".join("?" for _ in matching_active_predicates)
            with store.sm.get_connection(namespace) as conn:
                rows = conn.execute(
                    f"""SELECT c.*, s.file_path, s.origin, s.trust_tier
                        FROM claims_index c
                        JOIN sources_index s ON c.source_id = s.source_id
                        WHERE c.namespace = ? AND c.status = 'active'
                          AND c.predicate IN ({placeholders})
                        ORDER BY CASE WHEN c.predicate IN ('stated', 'has_note') THEN 1 ELSE 0 END ASC,
                                 c.valid_from DESC,
                                 c.rowid DESC""",
                    [namespace, *matching_active_predicates],
                ).fetchall()
            for r in rows:
                _add_row(dict(r))

        if not matched_rows:
            sorted_vec_hits = sorted(
                qualifying_vec_hits,
                key=lambda h: (
                    1 if h.get("predicate") in ("stated", "has_note") else 0,
                    h.get("distance", 999.0),
                ),
            )
            for h in sorted_vec_hits:
                _add_row(h)

    if not matched_rows:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return RetrievalResult(
            status="abstained",
            route=route,
            packed_prompt="I have no memory of that.",
            claims=[],
            citations=[],
            tokens_used=0,
            latency_ms=latency_ms,
        )

    # Step 5: Tiered Context Packing (L0 + L1 + L2) within token_budget
    shard_dir = store.sm.get_shard_dir(namespace)
    abstract_file = shard_dir / ".abstract.md"
    l0_content = abstract_file.read_text(encoding="utf-8").strip() if abstract_file.exists() else ""

    context_sections: List[str] = [f"# Retrieved Knowledge Context (Route: {route})"]
    if l0_content:
        context_sections.append(f"## OpenViking Tier L0 (Core Identity)\n{l0_content}")

    l1_lines: List[str] = ["## Tier L1 Active Triples"]
    for c in matched_rows:
        status_val = c.get("status", "active")
        status_suffix = f" [status={status_val}]" if status_val != "active" else ""
        l1_lines.append(
            f"- **{c['subject']}** -> **{c['predicate']}**: {c['object_val']} "
            f"(since {c['valid_from']}){status_suffix} [^{c['source_id']}]"
        )
    context_sections.append("\n".join(l1_lines))

    l2_lines: List[str] = ["## Tier L2 Exact Quotes & Provenance"]
    citations: List[str] = []
    citation_details: List[Citation] = []
    seen_sources: Set[str] = set()

    for c in matched_rows:
        span_text = store.read_verified_span(
            namespace, c["file_path"], c["byte_start"], c["byte_end"]
        )
        if not span_text or "[REDACTED" in span_text:
            continue
        cite_tag = f"[^{c['source_id']}]"
        if cite_tag not in citations:
            citations.append(cite_tag)
        if c["source_id"] not in seen_sources:
            seen_sources.add(c["source_id"])
            l2_lines.append(
                f"{cite_tag}: \"{span_text}\" ({c['file_path']} bytes {c['byte_start']}-{c['byte_end']})"
            )
            citation_details.append(
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
        packed_prompt = enc.decode(raw_tokens[:token_budget])
    else:
        packed_prompt = raw_packed

    tokens_used = len(enc.encode(packed_prompt))
    latency_ms = (time.perf_counter() - t0) * 1000.0

    claim_records = [_row_to_claim_record(r, namespace) for r in matched_rows]

    return RetrievalResult(
        status="ok",
        route=route,
        packed_prompt=packed_prompt,
        claims=claim_records,
        citations=citations,
        citation_details=citation_details,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
