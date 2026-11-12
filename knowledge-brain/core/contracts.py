"""Core Pydantic v2 data contracts for Knowledge Brain."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class SourceSpan(BaseModel):
    """Source provenance and byte-level evidence span."""
    model_config = ConfigDict(extra="ignore")

    source_id: str
    file_path: str
    sha256_hash: str
    origin: str
    trust_tier: int
    byte_start: int
    byte_end: int
    quote: str


class ClaimRecord(BaseModel):
    """Auditable atomic knowledge triple with temporal validity and provenance."""
    model_config = ConfigDict(extra="ignore")

    claim_id: str
    namespace: str
    subject: str
    predicate: str
    object_val: str
    status: Literal["active", "superseded", "disputed", "quarantined"]
    valid_from: str
    valid_to: Optional[str] = None
    source_id: str
    byte_start: int
    byte_end: int
    okf_file: str


class RecallResult(BaseModel):
    """Three-tier recall payload (L0 abstract, L1 claims, L2 source spans) with audit telemetry."""
    model_config = ConfigDict(extra="ignore")

    status: Literal["ok", "abstained"]
    answer_hint: str
    l0_abstract: str
    l1_claims: list[ClaimRecord]
    l2_quotes: list[SourceSpan]
    tokens_used: int
    baseline_full_history_tokens: int
    latency_ms: float


class DeletionReceipt(BaseModel):
    """Cryptographic audit receipt proving permanent deletion and unlearning."""
    model_config = ConfigDict(extra="ignore")

    receipt_id: str
    namespace: str
    target: str
    deleted_claim_ids: list[str]
    hmac_suppression_hash: str
    sqlite_byte_matches: int
    wal_byte_matches: int
    filesystem_byte_matches: int
    probe_abstentions: str
    sha256_after: str
    timestamp: str


class HandoffPacket(BaseModel):
    """OKF v0.2 structured cross-agent handoff packet."""
    model_config = ConfigDict(extra="ignore")

    okf_version: str = "0.2"
    namespace: str
    task_id: str
    status: str
    created_by_agent: str
    updated_at: str
    goal: str
    completed_steps: list[str]
    pending_steps: list[str]
    active_decisions: list[dict] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    relied_on_claims: list[str] = Field(default_factory=list)
    okf_file_path: str
    handoff_tokens: int
    full_history_tokens: int


SourceSpan.model_rebuild()
ClaimRecord.model_rebuild()
RecallResult.model_rebuild()
DeletionReceipt.model_rebuild()
HandoffPacket.model_rebuild()
