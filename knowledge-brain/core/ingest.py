"""Ingestion pipeline, UTF-8 byte span verification, and claim indexing."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import sqlite_vec
from fastembed import TextEmbedding

from core.contracts import (
    Citation,
    ClaimStatus,
    ExtractedCandidate,
    ORIGIN_TRUST_MAP,
    PREDICATE_REGISTRY,
)
from core.okf_compiler import compile_okf_files, now_iso
from core.policy import (
    apply_policy_and_decide_status,
    verify_exact_quote_span,
)
from core.predicates import get_target_okf_file


_GLOBAL_EMBED_MODEL: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    """Return cached fastembed BAAI/bge-small-en-v1.5 instance."""
    global _GLOBAL_EMBED_MODEL
    if _GLOBAL_EMBED_MODEL is None:
        _GLOBAL_EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _GLOBAL_EMBED_MODEL


def embed_text(text: str) -> bytes:
    """Generate 384-dim float embedding and serialize for sqlite-vec."""
    model = get_embedding_model()
    embeddings = list(model.embed([text]))
    vec = embeddings[0]
    return sqlite_vec.serialize_float32(vec)


def extract_heuristic_candidates(raw_text: str, default_subject: str = "user") -> List[ExtractedCandidate]:
    """Comprehensive regex and heuristic extractor for user facts, decisions, and tasks."""
    candidates: List[ExtractedCandidate] = []

    # 1. Favorite Color
    # e.g. "my favorite color is navy blue", "prefers teal color"
    for m in re.finditer(r"(?i)(?:my\s+)?favorite\s+color\s+(?:is|was)\s+([a-zA-Z\s]+?)(?:\s+(?:and|but|because|with|since|which)|\b[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        quote = raw_text[m.start():m.start(1) + len(m.group(1))].strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="favorite_color",
                object_val=val,
                exact_quote=quote,
            )
        )
    for m in re.finditer(r"(?i)prefers?\s+([a-zA-Z]+)\s+color", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="favorite_color",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 2. Location (lives_in)
    # e.g. "I live in Mangalore", "moved to Bengaluru", "based in Seattle"
    for m in re.finditer(r"(?i)(?:I\s+)?(?:live\s+in|reside\s+in|based\s+in|moved\s+to|located\s+in)\s+([a-zA-Z\s]+?)(?:\s+(?:and|but|because|with|since|which)|\b[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        quote = raw_text[m.start():m.start(1) + len(m.group(1))].strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="lives_in",
                object_val=val,
                exact_quote=quote,
            )
        )

    # 3. Preferred Database / Database Decision
    # e.g. "preferred database is PostgreSQL", "uses PostgreSQL database"
    for m in re.finditer(r"(?i)preferred\s+database\s+(?:is|to\s+use)\s+([a-zA-Z0-9_\-\s]+?)(?:\s+(?:and|but|because|with|since|which)|\b[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        quote = raw_text[m.start():m.start(1) + len(m.group(1))].strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="preferred_db",
                object_val=val,
                exact_quote=quote,
            )
        )
    for m in re.finditer(r"(?i)(?:use|uses|using)\s+([a-zA-Z0-9_\-]+)\s+(?:as\s+our\s+|for\s+)?database", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject="system",
                predicate="uses_database",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 4. Role & Employer
    # e.g. "my role is Principal Architect", "works as Backend Lead", "works at Acme Corp"
    for m in re.finditer(r"(?i)(?:my\s+)?role\s+is\s+([a-zA-Z0-9_\-\s]+?)(?:\s+(?:and|but|because|with|since|which)|\b[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        quote = raw_text[m.start():m.start(1) + len(m.group(1))].strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="role",
                object_val=val,
                exact_quote=quote,
            )
        )
    for m in re.finditer(r"(?i)(?:works?\s+at|employer\s+is)\s+([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="employer",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 5. Coding style & Language
    # e.g. "coding style is PEP8", "prefers functional style"
    for m in re.finditer(r"(?i)coding\s+style\s+(?:is|preference\s+is)\s+([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="coding_style",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 6. Graph Relationships: depends_on & manages
    # e.g. "auth_service depends on user_db", "emp_001 manages emp_042"
    for m in re.finditer(r"(?i)\b([a-zA-Z0-9_\-]+)\s+depends\s+on\s+([a-zA-Z0-9_\-]+)\b", raw_text):
        s, o = m.group(1).strip(), m.group(2).strip()
        candidates.append(
            ExtractedCandidate(
                subject=s,
                predicate="depends_on",
                object_val=o,
                exact_quote=m.group(0).strip(),
            )
        )
    for m in re.finditer(r"(?i)\b([a-zA-Z0-9_\-]+)\s+manages\s+([a-zA-Z0-9_\-]+)\b", raw_text):
        s, o = m.group(1).strip(), m.group(2).strip()
        candidates.append(
            ExtractedCandidate(
                subject=s,
                predicate="manages",
                object_val=o,
                exact_quote=m.group(0).strip(),
            )
        )

    # 7. Decisions and Constraints
    # e.g. "decided to use gRPC", "constraint: latency must be < 50ms"
    for m in re.finditer(r"(?i)decided(?:\s+to)?\s+([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject="architecture",
                predicate="decided",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )
    for m in re.finditer(r"(?i)constraint:\s*([a-zA-Z0-9_\-\s<>=%]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject="architecture",
                predicate="constraint",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 8. Tasks (goal, completed, pending, status)
    for m in re.finditer(r"(?i)task\s+goal:\s*([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="task_goal",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )
    for m in re.finditer(r"(?i)(?:task\s+)?completed:\s*([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="task_completed",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )
    for m in re.finditer(r"(?i)(?:task\s+)?pending:\s*([a-zA-Z0-9_\-\s]+?)(?:[.,\n]|$)", raw_text):
        val = m.group(1).strip()
        candidates.append(
            ExtractedCandidate(
                subject=default_subject,
                predicate="task_pending",
                object_val=val,
                exact_quote=m.group(0).strip("., \n"),
            )
        )

    # 9. Prompt Injection candidate (for explicit policy quarantine testing)
    for m in re.finditer(r"(?i)(?:ignore\s+previous\s+instructions|system\s+prompt|override\s+policy)[^\n]*", raw_text):
        val = m.group(0).strip()
        candidates.append(
            ExtractedCandidate(
                subject="adversary",
                predicate="has_note",
                object_val=val,
                exact_quote=val,
            )
        )

    # 10. Fallback contextual note if nothing else matched
    if not candidates and raw_text.strip():
        first_clause = re.split(r"[.\n]", raw_text.strip())[0].strip()
        if first_clause:
            candidates.append(
                ExtractedCandidate(
                    subject=default_subject,
                    predicate="has_note",
                    object_val=first_clause[:100],
                    exact_quote=first_clause,
                )
            )

    return candidates


def ingest_message(
    conn: sqlite3.Connection,
    shard_dir: Path,
    namespace: str,
    raw_text: str,
    session_id: str,
    origin: str = "user",
    candidates: Optional[List[ExtractedCandidate]] = None,
    llm_extractor: Optional[Callable[[str], List[ExtractedCandidate]]] = None,
) -> List[dict]:
    """Ingest a raw message into immutable raw logs, extract atomic claims,

    verify UTF-8 byte spans, apply conflict/quarantine policy, and update indexes.
    """
    timestamp = now_iso()
    trust_tier = ORIGIN_TRUST_MAP.get(origin.lower(), 1)

    # 1. Write raw natural language text to sources/session_XX.txt (Payload Plane L2)
    sources_dir = shard_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    source_filename = f"{session_id}.txt"
    source_file_path = sources_dir / source_filename
    rel_source_path = f"sources/{source_filename}"

    # Determine base byte offset in the source file
    base_byte_offset = 0
    if source_file_path.exists():
        base_byte_offset = source_file_path.stat().st_size

    # Append raw text and enforce physical disk flush with fsync
    with open(source_file_path, "a", encoding="utf-8") as f:
        f.write(raw_text)
        f.flush()
        os.fsync(f.fileno())

    # Compute SHA256 of the entire source file
    with open(source_file_path, "rb") as f:
        file_sha256 = hashlib.sha256(f.read()).hexdigest()

    # Register or update in sources_index
    source_id = f"src_{hashlib.md5(f'{session_id}_{base_byte_offset}'.encode()).hexdigest()[:8]}"
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO sources_index (source_id, file_path, sha256_hash, origin, trust_tier, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_id, rel_source_path, file_sha256, origin, trust_tier, timestamp),
    )

    # 2. Extract candidate claims
    if candidates is not None:
        extracted = candidates
    elif llm_extractor is not None:
        extracted = llm_extractor(raw_text)
    else:
        subject_name = namespace.split("/")[-1] if "users" in namespace else "user"
        extracted = extract_heuristic_candidates(raw_text, default_subject=subject_name)

    results: List[dict] = []

    # 3. Process each candidate
    for cand in extracted:
        # Verify exact quote span within raw_text
        span = verify_exact_quote_span(raw_text, cand.exact_quote)
        if span is None:
            # Reject hallucinated quotes completely!
            continue

        rel_byte_start, rel_byte_end = span
        abs_byte_start = base_byte_offset + rel_byte_start
        abs_byte_end = base_byte_offset + rel_byte_end

        # Canonicalize subject & predicate
        subj = cand.subject.strip()
        pred = cand.predicate.strip().lower()
        obj = cand.object_val.strip()
        okf_file = get_target_okf_file(pred)

        # Decide policy status
        status, reason, superseded_id = apply_policy_and_decide_status(
            conn=conn,
            namespace=namespace,
            subject=subj,
            predicate=pred,
            object_val=obj,
            origin=origin,
            trust_tier=trust_tier,
            raw_quote=cand.exact_quote,
        )

        # Handle superseding of old active claims
        if superseded_id:
            cursor.execute(
                """
                UPDATE claims_index 
                SET status = 'superseded', valid_to = ?
                WHERE claim_id = ?
                """,
                (timestamp, superseded_id),
            )
            # Remove superseded claim from active vector and fts index to prevent obsolete vector hits
            lineage_row = cursor.execute(
                "SELECT vec_rowid, fts_rowid FROM lineage_index WHERE claim_id = ?",
                (superseded_id,),
            ).fetchone()
            if lineage_row:
                if lineage_row["vec_rowid"] is not None:
                    cursor.execute("DELETE FROM vec_claims WHERE rowid = ?", (lineage_row["vec_rowid"],))
                if lineage_row["fts_rowid"] is not None:
                    cursor.execute("DELETE FROM fts_claims WHERE rowid = ?", (lineage_row["fts_rowid"],))

        # Insert new claim into claims_index
        claim_id = f"clm_{uuid.uuid4().hex[:12]}"
        cursor.execute(
            """
            INSERT INTO claims_index (
                claim_id, namespace, subject, predicate, object_val,
                status, valid_from, valid_to, source_id, byte_start, byte_end, okf_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                namespace,
                subj,
                pred,
                obj,
                status,
                timestamp,
                None,
                source_id,
                abs_byte_start,
                abs_byte_end,
                okf_file,
            ),
        )

        vec_rowid: Optional[int] = None
        fts_rowid: Optional[int] = None

        # Only index non-quarantined, active claims in Semantic Plane (vec0 & FTS5)
        if status == "active":
            # 1. Insert into FTS5
            cursor.execute(
                "INSERT INTO fts_claims (subject, predicate, object_val) VALUES (?, ?, ?)",
                (subj, pred, obj),
            )
            fts_rowid = cursor.lastrowid

            # 2. Insert into sqlite-vec with natural multi-token representation
            readable_pred = pred.replace("_", " ")
            text_for_embedding = f"{subj} user {readable_pred} is {obj}"
            emb_blob = embed_text(text_for_embedding)
            cursor.execute(
                "INSERT INTO vec_claims (embedding) VALUES (?)",
                (emb_blob,),
            )
            vec_rowid = cursor.lastrowid

        # Record lineage
        cursor.execute(
            """
            INSERT INTO lineage_index (claim_id, vec_rowid, fts_rowid, okf_file)
            VALUES (?, ?, ?, ?)
            """,
            (claim_id, vec_rowid, fts_rowid, okf_file),
        )

        results.append({
            "claim_id": claim_id,
            "subject": subj,
            "predicate": pred,
            "object_val": obj,
            "status": status,
            "reason": reason,
            "source_id": source_id,
            "byte_start": abs_byte_start,
            "byte_end": abs_byte_end,
        })

    conn.commit()

    # Recompile OpenViking L0 and Google OKF v0.2 files
    compile_okf_files(conn, shard_dir, namespace)

    return results
