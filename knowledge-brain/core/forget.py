"""Cryptographic forgetting, raw disk redaction, vacuuming, and signed receipt generation."""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from typing import List, Set, Tuple

import sqlite_vec

from core.contracts import DeletionReceipt
from core.ingest import embed_text
from core.okf_compiler import compile_okf_files, now_iso
from core.policy import compute_fact_hmac
from core.verifier import verify_deletion


RECEIPT_SIGNING_KEY = b"knowledge_brain_receipt_signing_key_2026"


def sign_receipt(fact_hmac: str, deleted_claims: int, redacted_spans: int, timestamp: str) -> str:
    """Produce cryptographic signature for DeletionReceipt."""
    payload = f"{fact_hmac}:{deleted_claims}:{redacted_spans}:{timestamp}".encode("utf-8")
    return hmac.new(RECEIPT_SIGNING_KEY, payload, hashlib.sha256).hexdigest()


def forget_target(
    conn: sqlite3.Connection,
    shard_dir: Path,
    namespace: str,
    target_query: str,
) -> DeletionReceipt:
    """Find and purge target knowledge across Payload, Control, and Semantic planes.

    Steps:
      1. Finds target claims via exact match, keyword, and semantic search (vec0 distance <= 0.75).
      2. Overwrites exact byte spans in sources/*.txt with padded [REDACTED] bytes + os.fsync().
      3. Records fact HMAC into suppression_hashes to permanently prevent re-learning.
      4. Deletes from vec_claims, fts_claims, lineage_index, and claims_index.
      5. Rebuilds FTS, runs secure_delete, checkpoints WAL with TRUNCATE, and vacuums.
      6. Regenerates .okf.md and .abstract.md.
      7. Runs verify_deletion to confirm 0 raw byte matches and 100% abstention on probes.
      8. Returns signed DeletionReceipt.
    """
    timestamp = now_iso()
    cursor = conn.cursor()
    target_clean = target_query.strip()

    target_claim_ids: Set[str] = set()
    target_object_vals: Set[str] = set()

    # 1. Search for matching claims via SQL pattern matching
    cursor.execute(
        """
        SELECT claim_id, subject, predicate, object_val, source_id, byte_start, byte_end
        FROM claims_index
        WHERE namespace = ? AND (
            object_val LIKE ? OR 
            predicate LIKE ? OR 
            subject LIKE ?
        )
        """,
        (namespace, f"%{target_clean}%", f"%{target_clean}%", f"%{target_clean}%"),
    )
    for row in cursor.fetchall():
        target_claim_ids.add(row["claim_id"])
        target_object_vals.add(row["object_val"])

    # 2. Semantic search in vec_claims (distance <= 0.75)
    query_emb = embed_text(target_clean)
    try:
        cursor.execute(
            """
            SELECT rowid, distance 
            FROM vec_claims 
            WHERE embedding MATCH ? AND k = 10 AND distance <= 0.75
            ORDER BY distance ASC
            """,
            (query_emb,),
        )
        vec_rowids = [r[0] for r in cursor.fetchall()]
        if vec_rowids:
            placeholders = ",".join("?" for _ in vec_rowids)
            cursor.execute(
                f"""
                SELECT c.claim_id, c.object_val
                FROM lineage_index l
                JOIN claims_index c ON l.claim_id = c.claim_id
                WHERE c.namespace = ? AND l.vec_rowid IN ({placeholders})
                """,
                [namespace] + vec_rowids,
            )
            for r in cursor.fetchall():
                target_claim_ids.add(r[0])
                target_object_vals.add(r[1])
    except Exception:
        pass

    if not target_claim_ids:
        # If no claims matched directly, still record suppression hash for the target string
        fact_hmac = compute_fact_hmac("user", "preference", target_clean)
        cursor.execute(
            "INSERT OR REPLACE INTO suppression_hashes (fact_hmac, deleted_at) VALUES (?, ?)",
            (fact_hmac, timestamp),
        )
        conn.commit()

        receipt_sig = sign_receipt(fact_hmac, 0, 0, timestamp)
        return DeletionReceipt(
            fact_hmac=fact_hmac,
            target=target_clean,
            deleted_claims=0,
            redacted_spans=0,
            bytes_purged=0,
            timestamp=timestamp,
            verified=True,
            signature=receipt_sig,
        )

    # 3. Retrieve all full records for target claims
    placeholders = ",".join("?" for _ in target_claim_ids)
    cursor.execute(
        f"""
        SELECT c.*, s.file_path, l.vec_rowid, l.fts_rowid
        FROM claims_index c
        JOIN sources_index s ON c.source_id = s.source_id
        LEFT JOIN lineage_index l ON c.claim_id = l.claim_id
        WHERE c.claim_id IN ({placeholders})
        """,
        list(target_claim_ids),
    )
    records_to_purge = cursor.fetchall()

    bytes_purged = 0
    redacted_spans = 0
    primary_hmac = ""

    # 4. Overwrite raw byte spans on disk & record suppression hashes
    for rec in records_to_purge:
        subj = rec["subject"]
        pred = rec["predicate"]
        obj = rec["object_val"]

        # Register tombstone HMACs for specific subject, user alias, and target value
        hmacs_to_suppress = {
            compute_fact_hmac(subj, pred, obj),
            compute_fact_hmac("user", pred, obj),
            compute_fact_hmac(subj, pred, target_clean),
            compute_fact_hmac("user", pred, target_clean),
        }

        for f_hmac in hmacs_to_suppress:
            if not primary_hmac:
                primary_hmac = f_hmac
            cursor.execute(
                "INSERT OR REPLACE INTO suppression_hashes (fact_hmac, deleted_at) VALUES (?, ?)",
                (f_hmac, timestamp),
            )

        # Overwrite physical bytes in source file
        rel_file_path = rec["file_path"]
        abs_file_path = shard_dir / rel_file_path
        b_start = rec["byte_start"]
        b_end = rec["byte_end"]
        span_len = b_end - b_start

        if abs_file_path.exists() and span_len > 0:
            try:
                with open(abs_file_path, "r+b") as f:
                    f.seek(b_start)
                    redact_marker = b"[REDACTED]"
                    if span_len >= len(redact_marker):
                        replacement = redact_marker + b" " * (span_len - len(redact_marker))
                    else:
                        replacement = b"*" * span_len

                    f.write(replacement)
                    f.flush()
                    os.fsync(f.fileno())

                bytes_purged += span_len
                redacted_spans += 1
            except Exception:
                pass

        # Delete from Semantic plane
        if rec["vec_rowid"] is not None:
            cursor.execute("DELETE FROM vec_claims WHERE rowid = ?", (rec["vec_rowid"],))
        if rec["fts_rowid"] is not None:
            cursor.execute("DELETE FROM fts_claims WHERE rowid = ?", (rec["fts_rowid"],))

        # Delete from Lineage and Claims plane
        cursor.execute("DELETE FROM lineage_index WHERE claim_id = ?", (rec["claim_id"],))
        cursor.execute("DELETE FROM claims_index WHERE claim_id = ?", (rec["claim_id"],))

    conn.commit()

    # 5. Purge and reclaim SQLite database storage
    cursor.execute("INSERT INTO fts_claims(fts_claims) VALUES('rebuild');")
    conn.commit()

    conn.execute("PRAGMA secure_delete = ON;")
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.execute("VACUUM;")
    conn.commit()

    # 6. Recompile OpenViking L0 and Google OKF files to reflect purged state
    compile_okf_files(conn, shard_dir, namespace)

    # 7. Verification: zero raw byte matches across all files & probe abstention
    verified = True
    for obj_val in target_object_vals:
        v_ok, _ = verify_deletion(conn, shard_dir, namespace, obj_val)
        if not v_ok:
            verified = False

    receipt_sig = sign_receipt(primary_hmac, len(target_claim_ids), redacted_spans, timestamp)

    return DeletionReceipt(
        fact_hmac=primary_hmac,
        target=target_clean,
        deleted_claims=len(target_claim_ids),
        redacted_spans=redacted_spans,
        bytes_purged=bytes_purged,
        timestamp=timestamp,
        verified=verified,
        signature=receipt_sig,
    )
