"""Control and Lineage Plane SQLite schema setup and shard connection management."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import sqlite_vec


SCHEMA_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA secure_delete = ON;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources_index (
    source_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    origin TEXT NOT NULL,
    trust_tier INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias TEXT PRIMARY KEY,
    canonical_subject TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims_index (
    claim_id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_val TEXT NOT NULL,
    status TEXT NOT NULL, -- 'active', 'superseded', 'disputed', 'quarantined'
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_id TEXT NOT NULL,
    byte_start INTEGER NOT NULL,
    byte_end INTEGER NOT NULL,
    okf_file TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources_index(source_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_namespace_status 
ON claims_index(namespace, status);

CREATE INDEX IF NOT EXISTS idx_claims_sub_pred 
ON claims_index(namespace, subject, predicate, status);

CREATE TABLE IF NOT EXISTS lineage_index (
    claim_id TEXT PRIMARY KEY,
    vec_rowid INTEGER,
    fts_rowid INTEGER,
    okf_file TEXT NOT NULL,
    FOREIGN KEY (claim_id) REFERENCES claims_index(claim_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppression_hashes (
    fact_hmac TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_claims USING fts5(
    subject,
    predicate,
    object_val
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_claims USING vec0(
    embedding float[384]
);
"""

# Track active connections by path so they can be reused or cleanly closed
_ACTIVE_SHARDS: Dict[str, sqlite3.Connection] = {}


def get_shard(memory_root: Union[str, Path], namespace: str) -> Tuple[sqlite3.Connection, Path]:
    """Initialize or connect to an isolated namespace shard.

    Creates directory layout `memory_root/{namespace}/sources/`, configures
    SQLite in WAL mode with secure_delete, loads sqlite-vec, and creates
    the full relational and virtual table schema.
    """
    clean_ns = namespace.strip("/\\").replace("\\", "/")
    root_path = Path(memory_root).resolve()
    shard_dir = root_path / clean_ns
    sources_dir = shard_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    db_path = str((shard_dir / "index.sqlite").resolve())

    # Reuse active connection if already open and healthy
    if db_path in _ACTIVE_SHARDS:
        conn = _ACTIVE_SHARDS[db_path]
        try:
            conn.execute("SELECT 1")
            return conn, shard_dir
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            del _ACTIVE_SHARDS[db_path]

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # Initialize schema
    conn.executescript(SCHEMA_DDL)
    conn.commit()

    _ACTIVE_SHARDS[db_path] = conn
    return conn, shard_dir


def close_shard(memory_root: Union[str, Path], namespace: str) -> None:
    """Close an active shard connection."""
    clean_ns = namespace.strip("/\\").replace("\\", "/")
    root_path = Path(memory_root).resolve()
    shard_dir = root_path / clean_ns
    db_path = str((shard_dir / "index.sqlite").resolve())

    if db_path in _ACTIVE_SHARDS:
        try:
            _ACTIVE_SHARDS[db_path].close()
        except Exception:
            pass
        del _ACTIVE_SHARDS[db_path]


def close_all_shards() -> None:
    """Close all open shard connections."""
    for path, conn in list(_ACTIVE_SHARDS.items()):
        try:
            conn.close()
        except Exception:
            pass
    _ACTIVE_SHARDS.clear()
