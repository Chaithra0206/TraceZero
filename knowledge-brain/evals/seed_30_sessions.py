"""Seed 30 realistic engineering sessions into a test shard."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from core.ingest import ingest_message
from core.schema import get_shard


SESSION_PROMPTS = [
    ("session_01", "Hello! I am setting up our new microservice architecture. My role is Principal Architect at Acme Corp."),
    ("session_02", "Please note that my favorite color is navy blue and I live in Mangalore."),
    ("session_03", "For our primary persistent storage, my preferred database is PostgreSQL."),
    ("session_04", "Our coding style is strict PEP8 with type annotations everywhere."),
    ("session_05", "Update: I moved to Bengaluru this week."),
    ("session_06", "We are defining services: auth_service depends on user_db."),
    ("session_07", "Also billing_service depends on auth_service."),
    ("session_08", "And notification_service depends on billing_service."),
    ("session_09", "emp_001 manages emp_042 in our engineering org."),
    ("session_10", "emp_042 manages emp_088 on the backend team."),
    ("session_11", "Architectural constraint: latency must be < 50ms for auth endpoints."),
    ("session_12", "Decided to use gRPC for all internal service communications."),
    ("session_13", "Decided to use Redis for distributed caching."),
    ("session_14", "Constraint: all microservices must run in isolated namespaces."),
    ("session_15", "Task goal: deploy payment gateway migration."),
    ("session_16", "Task completed: audit legacy payment contracts."),
    ("session_17", "Task completed: write OpenAPI 3.0 specification."),
    ("session_18", "Task completed: provision staging Postgres database."),
    ("session_19", "Task pending: implement webhook idempotency handlers."),
    ("session_20", "Task pending: execute blue-green cutover."),
    ("session_21", "Task pending: configure Prometheus alerts."),
    ("session_22", "Decided to use Argon2id for password hashing."),
    ("session_23", "Constraint: token expiry must be exactly 15 minutes."),
    ("session_24", "Task completed: implement rate limiting filter."),
    ("session_25", "Task pending: conduct load testing at 10k RPS."),
    ("session_26", "Note: staging environment URL is https://staging.internal.acme.net."),
    ("session_27", "Note: security review scheduled for Friday morning."),
    ("session_28", "Task completed: implement webhook idempotency handlers."),
    ("session_29", "Task pending: verify data consistency across replicas."),
    ("session_30", "Summary check: preparing handoff state for night shift oncall engineer."),
]


def seed_30_sessions(memory_root: Path, namespace: str = "acme/users/emp_042") -> Tuple[sqlite3.Connection, Path, List[dict]]:
    """Seed 30 progressive sessions into the specified shard."""
    conn, shard_dir = get_shard(memory_root, namespace)
    all_ingested = []

    for sess_id, text in SESSION_PROMPTS:
        ingested = ingest_message(
            conn=conn,
            shard_dir=shard_dir,
            namespace=namespace,
            raw_text=text,
            session_id=sess_id,
            origin="user",
        )
        all_ingested.extend(ingested)

    return conn, shard_dir, all_ingested


if __name__ == "__main__":
    import tempfile
    from core.schema import close_all_shards
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        conn, s_dir, ing = seed_30_sessions(Path(tmpdir))
        print(f"Successfully seeded 30 sessions with {len(ing)} total extracted claims in {s_dir}")
        close_all_shards()
