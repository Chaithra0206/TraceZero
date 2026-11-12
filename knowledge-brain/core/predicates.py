"""Predicate registry and classification helpers."""

from __future__ import annotations

from typing import Optional
from core.contracts import (
    Cardinality,
    PredicateMeta,
    PREDICATE_REGISTRY,
    StorageTier,
)


def get_predicate_meta(name: str) -> PredicateMeta:
    """Return metadata for a predicate, falling back to a safe multi-valued default."""
    canonical = name.strip().lower()
    if canonical in PREDICATE_REGISTRY:
        return PREDICATE_REGISTRY[canonical]
    return PredicateMeta(
        name=canonical,
        cardinality=Cardinality.MULTI,
        storage=StorageTier.VECTOR_NOTE,
        okf_file="notes.okf.md",
        description="Dynamic predicate",
    )


def is_single_valued(name: str) -> bool:
    """Check if predicate has single cardinality."""
    return get_predicate_meta(name).cardinality == Cardinality.SINGLE


def get_target_okf_file(name: str) -> str:
    """Return target OKF file for the predicate."""
    return get_predicate_meta(name).okf_file


__all__ = [
    "Cardinality",
    "PredicateMeta",
    "PREDICATE_REGISTRY",
    "StorageTier",
    "get_predicate_meta",
    "is_single_valued",
    "get_target_okf_file",
]

