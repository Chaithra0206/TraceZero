"""High-level Python API for Knowledge Brain tools."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from core.contracts import DeletionReceipt, HandoffPacket, RetrievalResult
from core.forget import forget_target
from core.handoff import handoff_create as _handoff_create, handoff_get as _handoff_get
from core.ingest import ingest_message
from core.retrieval import recall_context
from core.schema import get_shard
from core.verifier import verify_deletion as _verify_deletion


DEFAULT_MEMORY_ROOT = Path(os.environ.get("MEMORY_ROOT", "./memory_root"))


class KnowledgeBrainAPI:
    """Enterprise API wrapping Knowledge Brain operations."""

    def __init__(self, memory_root: Optional[Path] = None):
        self.memory_root = (memory_root or DEFAULT_MEMORY_ROOT).resolve()
        self.memory_root.mkdir(parents=True, exist_ok=True)

    def remember(
        self,
        namespace: str,
        text: str,
        origin: str = "user",
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        sess_id = session_id or f"session_{uuid.uuid4().hex[:6]}"
        return ingest_message(
            conn=conn,
            shard_dir=shard_dir,
            namespace=namespace,
            raw_text=text,
            session_id=sess_id,
            origin=origin,
        )

    def recall(
        self,
        namespace: str,
        query: str,
        token_budget: int = 800,
    ) -> RetrievalResult:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        return recall_context(
            conn=conn,
            shard_dir=shard_dir,
            namespace=namespace,
            query=query,
            token_budget=token_budget,
        )

    def forget(
        self,
        namespace: str,
        target: str,
    ) -> DeletionReceipt:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        return forget_target(
            conn=conn,
            shard_dir=shard_dir,
            namespace=namespace,
            target_query=target,
        )

    def verify_deletion(
        self,
        namespace: str,
        target_val: str,
    ) -> Dict[str, Any]:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        verified, details = _verify_deletion(conn, shard_dir, namespace, target_val)
        details["verified"] = verified
        return details

    def explain(
        self,
        namespace: str,
        claim_id: str,
    ) -> Dict[str, Any]:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*, s.file_path, s.origin, s.trust_tier, s.sha256_hash, s.created_at as source_created_at
            FROM claims_index c
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.claim_id = ?
            """,
            (namespace, claim_id),
        )
        row = cursor.fetchone()
        if not row:
            return {"error": f"Claim {claim_id} not found in namespace {namespace}"}

        res = dict(row)
        # Read exact quote bytes from source file
        raw_file = shard_dir / row["file_path"]
        if raw_file.exists():
            with open(raw_file, "rb") as f:
                f.seek(row["byte_start"])
                raw_bytes = f.read(row["byte_end"] - row["byte_start"])
                res["exact_quote"] = raw_bytes.decode("utf-8", errors="replace")
        return res

    def history(
        self,
        namespace: str,
        subject: str,
        predicate: str,
    ) -> List[Dict[str, Any]]:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.claim_id, c.subject, c.predicate, c.object_val, c.status, 
                   c.valid_from, c.valid_to, c.source_id, s.origin, s.trust_tier, s.file_path
            FROM claims_index c
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.subject = ? AND c.predicate = ?
            ORDER BY c.valid_from ASC
            """,
            (namespace, subject, predicate),
        )
        return [dict(r) for r in cursor.fetchall()]

    def quarantine_list(
        self,
        namespace: str,
    ) -> List[Dict[str, Any]]:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.claim_id, c.subject, c.predicate, c.object_val, c.status, 
                   c.valid_from, c.source_id, s.origin, s.trust_tier, s.file_path
            FROM claims_index c
            JOIN sources_index s ON c.source_id = s.source_id
            WHERE c.namespace = ? AND c.status IN ('quarantined', 'disputed')
            ORDER BY c.valid_from DESC
            """,
            (namespace,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def handoff_create(
        self,
        namespace: str,
        task_goal: str,
        completed_steps: List[str],
        pending_steps: List[str],
        blocked_steps: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        decisions: Optional[Dict[str, str]] = None,
    ) -> HandoffPacket:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        return _handoff_create(
            conn=conn,
            shard_dir=shard_dir,
            namespace=namespace,
            task_goal=task_goal,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            blocked_steps=blocked_steps,
            constraints=constraints,
            decisions=decisions,
        )

    def handoff_get(
        self,
        namespace: str,
    ) -> HandoffPacket:
        conn, shard_dir = get_shard(self.memory_root, namespace)
        return _handoff_get(shard_dir, namespace)

