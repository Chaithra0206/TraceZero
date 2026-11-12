"""Agent 1 (Architect / Planner Agent).

Connects to Knowledge Brain mcp_server.py as an MCP stdio client.
Records architectural decisions across multiple turns, generates Step 1 DDL artifact,
and creates an OKF v0.2 task handoff packet for Agent 2.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NAMESPACE = "acme_corp/users/emp_042"
TASK_ID = "payment_db_migration"


async def run_agent1():
    repo_root = Path(__file__).resolve().parent.parent
    artifacts_dir = repo_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" [AGENT 1: ARCHITECT] Initializing MCP client session...")
    print("=" * 70)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py", "--transport", "stdio"],
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(" Connected to Knowledge Brain MCP Server.")

            # Turn 1: Remember Target Database Decision
            turn1_text = "Payment service migration will switch from MongoDB to PostgreSQL 16."
            print(f"\n[Turn 1] Recording architectural decision: '{turn1_text}'")
            res1 = await session.call_tool(
                "remember",
                {"namespace": NAMESPACE, "text": turn1_text, "origin": "architect_session"},
            )
            data1 = json.loads(res1.content[0].text) if hasattr(res1.content[0], "text") else res1
            print(f" Recorded turn 1 claims: {data1.get('claims')}")

            # Turn 2: Remember Primary Key Format Decision
            turn2_text = "All primary keys in payment tables must use uuidv7."
            print(f"\n[Turn 2] Recording architectural decision: '{turn2_text}'")
            res2 = await session.call_tool(
                "remember",
                {"namespace": NAMESPACE, "text": turn2_text, "origin": "architect_session"},
            )
            data2 = json.loads(res2.content[0].text) if hasattr(res2.content[0], "text") else res2
            print(f" Recorded turn 2 claims: {data2.get('claims')}")

            # Complete Step 1: Generate PostgreSQL 16 DDL Schema with uuidv7
            print("\n[Step 1 Execution] Generating PostgreSQL 16 DDL Schema (step1_schema.sql)...")
            ddl_sql = """-- PostgreSQL 16 DDL Schema for Payment Service Migration
-- Specification: PostgreSQL 16 + uuidv7 primary keys

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY, -- uuidv7 time-ordered unique identifier
    customer_id VARCHAR(64) NOT NULL,
    amount_cents BIGINT NOT NULL CHECK (amount_cents >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_audit_log (
    log_id UUID PRIMARY KEY, -- uuidv7
    payment_id UUID NOT NULL REFERENCES payments(payment_id) ON DELETE CASCADE,
    previous_state VARCHAR(32),
    new_state VARCHAR(32) NOT NULL,
    changed_by VARCHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_idempotency ON payments(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_audit_payment_id ON payment_audit_log(payment_id);
"""
            schema_path = artifacts_dir / "step1_schema.sql"
            schema_path.write_text(ddl_sql, encoding="utf-8")
            print(f" Wrote artifact to: {schema_path}")

            # Call handoff_create to prepare handoff packet for Agent 2
            print("\n[Handoff Creation] Calling handoff_create on Knowledge Brain...")
            handoff_res = await session.call_tool(
                "handoff_create",
                {
                    "namespace": NAMESPACE,
                    "task_id": TASK_ID,
                    "goal": "Payment service database migration from MongoDB to PostgreSQL 16 with uuidv7 keys.",
                    "completed_steps": ["Step 1: DDL Schema generated"],
                    "pending_steps": [
                        "Step 2: Write Python idempotent dual-write backfill script honoring active DB & key constraints"
                    ],
                    "open_questions": ["Batch size for backfill workers"],
                    "created_by_agent": "agent1_architect",
                },
            )
            handoff_data = json.loads(handoff_res.content[0].text) if hasattr(handoff_res.content[0], "text") else handoff_res

            print("=" * 70)
            print(" [AGENT 1: ARCHITECT] Handoff Packet Generated Successfully!")
            print(f" Task ID           : {handoff_data.get('task_id')}")
            print(f" Status            : {handoff_data.get('status')}")
            print(f" OKF File Path     : {handoff_data.get('okf_file_path')}")
            print(f" Relied-on Claims  : {handoff_data.get('relied_on_claims')}")
            print(f" Handoff Tokens    : {handoff_data.get('handoff_tokens')} tokens")
            print("=" * 70)


def main():
    asyncio.run(run_agent1())


if __name__ == "__main__":
    main()
