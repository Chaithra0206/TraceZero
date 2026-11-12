from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class TrustTier(IntEnum):
    DOC_WEB = 1
    TOOL = 2
    USER = 3

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.name == value.upper():
                    return member
        return super()._missing_(value)


class ClaimStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    QUARANTINED = "quarantined"
    DELETED = "deleted"

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower() or member.name == value.upper():
                    return member
        return super()._missing_(value)


class SourceRecord(BaseModel):
    source_id: str
    file_path: str
    sha256_hash: str
    origin: str  # 'user' | 'tool' | 'doc' | 'web'
    trust_tier: TrustTier
    created_at: str


class ClaimRecord(BaseModel):
    claim_id: str
    namespace: str
    subject: str
    predicate: str
    object_val: str
    status: ClaimStatus = ClaimStatus.ACTIVE
    valid_from: str
    valid_to: Optional[str] = None
    source_id: str
    byte_start: int
    byte_end: int
    okf_file: str = "preferences.okf.md"

    @model_validator(mode="before")
    @classmethod
    def _handle_object_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "object" in data and "object_val" not in data:
                data["object_val"] = data.pop("object")
        return data

    @property
    def object(self) -> str:
        return self.object_val

    @property
    def claim_text(self) -> str:
        return f"{self.subject} {self.predicate} {self.object_val}"


class RetrievalResult(BaseModel):
    status: str  # 'ok' | 'abstained'
    packed_prompt: str
    claims: List[ClaimRecord] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    tokens_used: int
    latency_ms: float


class DeletionReceipt(BaseModel):
    receipt_id: str
    namespace: str
    target_query: str
    deleted_claim_ids: List[str]
    redacted_source_spans: List[str]
    suppression_hmacs: List[str]
    fts_rebuilt: bool
    vacuum_completed: bool
    byte_scan_matches: int
    scrubbed_files_sha256: Dict[str, str]
    timestamp: str

    @property
    def is_zero_trace_verified(self) -> bool:
        """Returns True iff no residual bytes remain and indices/pages are rebuilt."""
        return (
            self.byte_scan_matches == 0
            and self.fts_rebuilt
            and self.vacuum_completed
        )


class HandoffPacket(BaseModel):
    packet_id: str
    source_agent: str
    target_agent: str
    namespace: str
    claims: List[ClaimRecord] = Field(default_factory=list)
    packed_prompt: str = ""
    tokens_used: int = 0
    timestamp: str = ""
    context_summary: str = ""

    @model_validator(mode="before")
    @classmethod
    def _handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "from_agent" in data and "source_agent" not in data:
                data["source_agent"] = data.pop("from_agent")
            if "to_agent" in data and "target_agent" not in data:
                data["target_agent"] = data.pop("to_agent")
            if "active_claims" in data and "claims" not in data:
                data["claims"] = data.pop("active_claims")
            if "created_at" in data and "timestamp" not in data:
                data["timestamp"] = data.pop("created_at")
            if "task_summary" in data and "context_summary" not in data:
                data["context_summary"] = data.pop("task_summary")
        return data

    @property
    def from_agent(self) -> str:
        return self.source_agent

    @property
    def to_agent(self) -> str:
        return self.target_agent

    @property
    def task_summary(self) -> str:
        return self.context_summary

    @property
    def active_claims(self) -> List[ClaimRecord]:
        return [c for c in self.claims if c.status == ClaimStatus.ACTIVE]
