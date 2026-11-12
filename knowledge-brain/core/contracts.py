from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
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


class Cardinality(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class StorageTier(str, Enum):
    PROMPT_L0 = "PROMPT_L0"
    GRAPH_CLAIM = "GRAPH_CLAIM"
    OKF_FILE = "OKF_FILE"
    SQL_CODE = "SQL_CODE"
    VECTOR_NOTE = "VECTOR_NOTE"


@dataclass(frozen=True)
class PredicateMeta:
    name: str
    cardinality: Cardinality
    storage: StorageTier
    okf_file: str
    description: str = ""


ORIGIN_TRUST_MAP: Dict[str, TrustTier] = {
    "user": TrustTier.USER,
    "tool": TrustTier.TOOL,
    "doc": TrustTier.DOC_WEB,
    "web": TrustTier.DOC_WEB,
}

# Standard predicate registry covering single/multi cardinality and storage tiers
PREDICATE_REGISTRY: Dict[str, PredicateMeta] = {
    "favorite_color": PredicateMeta(
        name="favorite_color",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="User's primary favorite color",
    ),
    "role": PredicateMeta(
        name="role",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="Job title or primary engineering role",
    ),
    "coding_style": PredicateMeta(
        name="coding_style",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="Preferred coding standards, style guides, formatting",
    ),
    "lives_in": PredicateMeta(
        name="lives_in",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="Current residence city or location",
    ),
    "employer": PredicateMeta(
        name="employer",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="preferences.okf.md",
        description="Current organization or employer",
    ),
    "preferred_db": PredicateMeta(
        name="preferred_db",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="Default database preference for projects",
    ),
    "programming_language": PredicateMeta(
        name="programming_language",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="Primary programming language",
    ),
    "timezone": PredicateMeta(
        name="timezone",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.PROMPT_L0,
        okf_file="preferences.okf.md",
        description="User working timezone",
    ),
    "prefers": PredicateMeta(
        name="prefers",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="preferences.okf.md",
        description="General multi-valued preference",
    ),
    "framework": PredicateMeta(
        name="framework",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="preferences.okf.md",
        description="Preferred libraries or frameworks",
    ),
    "uses_database": PredicateMeta(
        name="uses_database",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="decisions.okf.md",
        description="Database in use for a particular service or project",
    ),
    "manages": PredicateMeta(
        name="manages",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="decisions.okf.md",
        description="Management or supervisory relation",
    ),
    "depends_on": PredicateMeta(
        name="depends_on",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.GRAPH_CLAIM,
        okf_file="decisions.okf.md",
        description="Service or module dependency relation",
    ),
    "decided": PredicateMeta(
        name="decided",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.OKF_FILE,
        okf_file="decisions.okf.md",
        description="Recorded architectural or technical decisions",
    ),
    "constraint": PredicateMeta(
        name="constraint",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.OKF_FILE,
        okf_file="decisions.okf.md",
        description="Architectural or operational constraints",
    ),
    "architecture_style": PredicateMeta(
        name="architecture_style",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.OKF_FILE,
        okf_file="decisions.okf.md",
        description="High level architecture paradigm",
    ),
    "auth_strategy": PredicateMeta(
        name="auth_strategy",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.OKF_FILE,
        okf_file="decisions.okf.md",
        description="Authentication and authorization strategy",
    ),
    "task_goal": PredicateMeta(
        name="task_goal",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Active sprint or task objective",
    ),
    "task_completed": PredicateMeta(
        name="task_completed",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Finished task milestone",
    ),
    "task_pending": PredicateMeta(
        name="task_pending",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Remaining or next task item",
    ),
    "task_status": PredicateMeta(
        name="task_status",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Current workflow phase or status",
    ),
    "task_blocked": PredicateMeta(
        name="task_blocked",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Blocked tasks or blockers",
    ),
    "task_assigned_to": PredicateMeta(
        name="task_assigned_to",
        cardinality=Cardinality.SINGLE,
        storage=StorageTier.OKF_FILE,
        okf_file="tasks.okf.md",
        description="Assignee of current work",
    ),
    "has_note": PredicateMeta(
        name="has_note",
        cardinality=Cardinality.MULTI,
        storage=StorageTier.VECTOR_NOTE,
        okf_file="notes.okf.md",
        description="General contextual note or observation",
    ),
}


class ExtractedCandidate(BaseModel):
    subject: str = Field(..., description="Entity or agent subject, e.g. 'user' or service name")
    predicate: str = Field(..., description="Canonical predicate from registry")
    object_val: str = Field(..., description="Extracted scalar value")
    exact_quote: str = Field(..., description="Exact substring verbatim from raw text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractionBatch(BaseModel):
    session_id: str
    origin: str = "user"
    candidates: List[ExtractedCandidate] = Field(default_factory=list)


class Citation(BaseModel):
    source_id: str
    file_path: str
    byte_start: int
    byte_end: int
    exact_quote: Optional[str] = None


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
    packed_prompt: str = ""
    claims: List[ClaimRecord] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    route: str = "HYBRID_TIERED"
    citation_details: List[Citation] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "packed_context" in data and "packed_prompt" not in data:
                data["packed_prompt"] = data.pop("packed_context")
        return data

    @property
    def packed_context(self) -> str:
        return self.packed_prompt


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
