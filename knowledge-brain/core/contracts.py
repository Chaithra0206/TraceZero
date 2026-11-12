"""Contracts, schema types, and predicate definitions for Knowledge Brain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Cardinality(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class StorageTier(str, Enum):
    PROMPT_L0 = "PROMPT_L0"
    GRAPH_CLAIM = "GRAPH_CLAIM"
    OKF_FILE = "OKF_FILE"
    SQL_CODE = "SQL_CODE"
    VECTOR_NOTE = "VECTOR_NOTE"


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class PredicateMeta:
    name: str
    cardinality: Cardinality
    storage: StorageTier
    okf_file: str
    description: str = ""


ORIGIN_TRUST_MAP: Dict[str, int] = {
    "user": 3,
    "tool": 2,
    "doc": 1,
    "web": 1,
}

# 24 standard predicates covering single/multi cardinality and diverse storage tiers
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


class RetrievalResult(BaseModel):
    status: str = Field(..., description="'ok' or 'abstained'")
    route: str = Field(..., description="'SQL_AGGREGATE', 'GRAPH_CTE', 'TEMPORAL_HISTORY', or 'HYBRID_TIERED'")
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    packed_context: str = Field(default="")
    tokens_used: int = Field(default=0)


class DeletionReceipt(BaseModel):
    fact_hmac: str
    target: str
    deleted_claims: int
    redacted_spans: int
    bytes_purged: int
    timestamp: str
    verified: bool
    signature: str


class HandoffPacket(BaseModel):
    namespace: str
    task_goal: str
    completed_steps: List[str] = Field(default_factory=list)
    pending_steps: List[str] = Field(default_factory=list)
    blocked_steps: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    active_decisions: Dict[str, str] = Field(default_factory=dict)
    source_okf_path: str
    timestamp: str

