"""High-level Python API for Knowledge Brain tools backed by MemoryStore."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.contracts import DeletionReceipt, HandoffPacket, RetrievalResult
from core.ingest import ingest_message
from core.retrieval import recall_context
from core.storage_api import MemoryStore
from core.verifier import compute_shard_hashes, scan_shard_bytes
from server.handoff import handoff_create as _handoff_create, handoff_get as _handoff_get

DEFAULT_MEMORY_ROOT = Path(os.environ.get("MEMORY_ROOT", "./memory_root"))


class KnowledgeBrainAPI:
    """Enterprise API wrapping Knowledge Brain operations via MemoryStore."""

    def __init__(self, memory_root: Optional[Path] = None):
        self.memory_root = (memory_root or DEFAULT_MEMORY_ROOT).resolve()
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.store = MemoryStore(root_dir=str(self.memory_root))

    def remember(
        self,
        namespace: str,
        text: str,
        origin: str = "user",
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sess_id = session_id or f"session_{uuid.uuid4().hex[:6]}"
        return ingest_message(
            store=self.store,
            namespace=namespace,
            text=text,
            origin=origin,
            session_id=sess_id,
        )

    def recall(
        self,
        namespace: str,
        query: str,
        token_budget: int = 800,
    ) -> RetrievalResult:
        return recall_context(
            store=self.store,
            namespace=namespace,
            query=query,
            token_budget=token_budget,
        )

    def forget(
        self,
        namespace: str,
        target: str,
    ) -> DeletionReceipt:
        return self.store.forget(namespace=namespace, target_query=target)

    def verify_deletion(
        self,
        namespace: str,
        target_val: str,
    ) -> Dict[str, Any]:
        shard_dir = self.store.sm.get_shard_dir(namespace)
        matches = scan_shard_bytes(shard_dir, [target_val])
        hashes = compute_shard_hashes(shard_dir)
        return {
            "verified": matches == 0,
            "byte_scan_matches": matches,
            "scrubbed_files_sha256": hashes,
        }

    def explain(
        self,
        namespace: str,
        claim_id: str,
    ) -> Dict[str, Any]:
        res = self.store.explain_claim(namespace, claim_id)
        if not res:
            return {"error": f"Claim {claim_id} not found in namespace {namespace}"}
        return res

    def history(
        self,
        namespace: str,
        subject: str,
        predicate: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.store.get_claim_history(namespace, subject, predicate)

    def quarantine_list(
        self,
        namespace: str,
    ) -> List[Dict[str, Any]]:
        return self.store.list_quarantined(namespace)

    def confirm_quarantine(
        self,
        namespace: str,
        claim_id: str,
    ) -> bool:
        return self.store.confirm_quarantined_claim(namespace, claim_id)

    def handoff_create(
        self,
        namespace: str,
        task_id: str,
        goal: str,
        completed_steps: List[str],
        pending_steps: List[str],
        open_questions: Optional[List[str]] = None,
        relied_on_claim_ids: Optional[List[str]] = None,
        agent_id: str = "agent_a_claude",
    ) -> HandoffPacket:
        return _handoff_create(
            store=self.store,
            namespace=namespace,
            task_id=task_id,
            goal=goal,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            open_questions=open_questions,
            relied_on_claim_ids=relied_on_claim_ids,
            agent_id=agent_id,
        )

    def handoff_get(
        self,
        namespace: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _handoff_get(self.store, namespace, task_id=task_id)
