from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    "user_session": TrustTier.USER,
    "agent_interaction": TrustTier.USER,
    "tool": TrustTier.TOOL,
    "doc": TrustTier.DOC_WEB,
    "web": TrustTier.DOC_WEB,
    "external_untrusted": TrustTier.DOC_WEB,
    "untrusted_scrape": TrustTier.DOC_WEB,
    "poisoned": TrustTier.DOC_WEB,
}

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


class SourceSpan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str
    file_path: str
    sha256_hash: str
    origin: str
    trust_tier: int
    byte_start: int
    byte_end: int
    quote: str


class SourceRecord(BaseModel):
    source_id: str
    file_path: str
    sha256_hash: str
    origin: str  # 'user' | 'tool' | 'doc' | 'web'
    trust_tier: TrustTier
    created_at: str


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


class RecallResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["ok", "abstained"]
    answer_hint: str
    l0_abstract: str
    l1_claims: List[ClaimRecord] = Field(default_factory=list)
    l2_quotes: List[SourceSpan] = Field(default_factory=list)
    tokens_used: int
    baseline_full_history_tokens: int
    latency_ms: float


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    model_config = ConfigDict(extra="ignore")

    receipt_id: str
    namespace: str
    target_query: str = ""
    target: str = ""
    deleted_claim_ids: List[str] = Field(default_factory=list)
    redacted_source_spans: List[str] = Field(default_factory=list)
    suppression_hmacs: List[str] = Field(default_factory=list)
    hmac_suppression_hash: str = ""
    fts_rebuilt: bool = True
    vacuum_completed: bool = True
    byte_scan_matches: int = 0
    sqlite_byte_matches: int = 0
    wal_byte_matches: int = 0
    filesystem_byte_matches: int = 0
    probe_abstentions: str = "VERIFIED_ABSTAINED_10_PROBES"
    sha256_after: str = ""
    scrubbed_files_sha256: Dict[str, str] = Field(default_factory=dict)
    timestamp: str = ""

    @model_validator(mode="before")
    @classmethod
    def _sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "target" in data and "target_query" not in data:
                data["target_query"] = data["target"]
            elif "target_query" in data and "target" not in data:
                data["target"] = data["target_query"]
            if "hmac_suppression_hash" in data and "suppression_hmacs" not in data:
                data["suppression_hmacs"] = (
                    [data["hmac_suppression_hash"]] if data["hmac_suppression_hash"] else []
                )
            elif "suppression_hmacs" in data and "hmac_suppression_hash" not in data:
                hmacs = data["suppression_hmacs"]
                data["hmac_suppression_hash"] = hmacs[0] if hmacs else ""
        return data

    @property
    def is_zero_trace_verified(self) -> bool:
        """Returns True iff no residual bytes remain and indices/pages are rebuilt."""
        return (
            self.byte_scan_matches == 0
            and self.fts_rebuilt
            and self.vacuum_completed
        )


class HandoffPacket(BaseModel):
    model_config = ConfigDict(extra="ignore")

    okf_version: str = "0.2"
    packet_id: str = ""
    source_agent: str = "agent_a_claude"
    target_agent: str = "agent_b"
    created_by_agent: str = "agent_a_claude"
    status: str = "in_progress"
    updated_at: str = ""
    namespace: str = ""
    task_id: str = ""
    goal: str = ""
    completed_steps: List[str] = Field(default_factory=list)
    pending_steps: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    relied_on_claim_ids: List[str] = Field(default_factory=list)
    relied_on_claims: List[str] = Field(default_factory=list)
    verified_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    active_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    source_okf_path: str = "tasks.okf.md"
    okf_file_path: str = "tasks.okf.md"
    claims: List[ClaimRecord] = Field(default_factory=list)
    packed_prompt: str = ""
    tokens_used: int = 0
    handoff_tokens: int = 0
    full_history_tokens: int = 0
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
            if "created_by_agent" in data and "source_agent" not in data:
                data["source_agent"] = data["created_by_agent"]
            elif "source_agent" in data and "created_by_agent" not in data:
                data["created_by_agent"] = data["source_agent"]
            if "active_claims" in data and "claims" not in data:
                data["claims"] = data.pop("active_claims")
            if "created_at" in data and "timestamp" not in data:
                data["timestamp"] = data.pop("created_at")
            if "updated_at" in data and not data.get("timestamp"):
                data["timestamp"] = data["updated_at"]
            elif "timestamp" in data and not data.get("updated_at"):
                data["updated_at"] = data["timestamp"]
            if "task_summary" in data and "context_summary" not in data:
                data["context_summary"] = data.pop("task_summary")
            if "task_goal" in data and "goal" not in data:
                data["goal"] = data.pop("task_goal")
            if "relied_on_claim_ids" in data and "relied_on_claims" not in data:
                data["relied_on_claims"] = list(data["relied_on_claim_ids"])
            elif "relied_on_claims" in data and "relied_on_claim_ids" not in data:
                data["relied_on_claim_ids"] = list(data["relied_on_claims"])
            if "verified_decisions" in data and "active_decisions" not in data:
                data["active_decisions"] = list(data["verified_decisions"])
            elif "active_decisions" in data and "verified_decisions" not in data:
                data["verified_decisions"] = list(data["active_decisions"])
            if "source_okf_path" in data and "okf_file_path" not in data:
                data["okf_file_path"] = data["source_okf_path"]
            elif "okf_file_path" in data and "source_okf_path" not in data:
                data["source_okf_path"] = data["okf_file_path"]
            if "tokens_used" in data and "handoff_tokens" not in data:
                data["handoff_tokens"] = data["tokens_used"]
            elif "handoff_tokens" in data and "tokens_used" not in data:
                data["tokens_used"] = data["handoff_tokens"]
        return data

    @property
    def from_agent(self) -> str:
        return self.source_agent

    @property
    def to_agent(self) -> str:
        return self.target_agent

    @property
    def task_summary(self) -> str:
        return self.context_summary or self.goal

    @property
    def task_goal(self) -> str:
        return self.goal

    @property
    def active_claims(self) -> List[ClaimRecord]:
        return [c for c in self.claims if c.status == ClaimStatus.ACTIVE]


SourceSpan.model_rebuild()
ClaimRecord.model_rebuild()
RecallResult.model_rebuild()
RetrievalResult.model_rebuild()
DeletionReceipt.model_rebuild()
HandoffPacket.model_rebuild()
