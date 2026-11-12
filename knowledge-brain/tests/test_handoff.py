from core import MemoryStore, ingest_message
from server.handoff import handoff_create, handoff_get


def test_cross_agent_handoff_survives_restart(tmp_path):
    ns = "acme_corp/projects/billing_v2"

    # --- AGENT A (Claude) ---
    store_a = MemoryStore(root_dir=str(tmp_path))

    res_1 = ingest_message(
        store=store_a,
        namespace=ns,
        text="We decided to use PostgreSQL with Drizzle ORM.",
        origin="user",
        source_id="src_dec_1",
        session_id="session_a1",
    )
    res_2 = ingest_message(
        store=store_a,
        namespace=ns,
        text="We decided to use UUIDv7 for primary keys.",
        origin="user",
        source_id="src_dec_2",
        session_id="session_a1",
    )
    claim_ids = [res_1[0]["claim_id"], res_2[0]["claim_id"]]

    packet = handoff_create(
        store=store_a,
        namespace=ns,
        task_id="task_billing_schema_01",
        goal="Design and migrate the billing_v2 database schema",
        completed_steps=["Step 1: Define core tables and primary key conventions"],
        pending_steps=[
            "Step 2: Write Drizzle ORM schema definitions",
            "Step 3: Generate and run initial PostgreSQL migration",
        ],
        open_questions=["Should invoice line items be partitioned by quarter?"],
        relied_on_claim_ids=claim_ids,
        agent_id="agent_a_claude",
    )

    assert packet.task_id == "task_billing_schema_01"
    assert "[^src_dec_1]" in packet.citations
    assert "[^src_dec_2]" in packet.citations

    # Simulate process kill / zero in-memory state by creating a fresh MemoryStore
    del store_a

    # --- AGENT B (Cursor / GPT) ---
    store_b = MemoryStore(root_dir=str(tmp_path))
    resumed = handoff_get(store=store_b, namespace=ns, task_id="task_billing_schema_01")

    assert resumed["status"] == "ok"
    assert resumed["task_id"] == "task_billing_schema_01"
    assert resumed["created_by_agent"] == "agent_a_claude"
    assert resumed["pending_steps"] == [
        "Step 2: Write Drizzle ORM schema definitions",
        "Step 3: Generate and run initial PostgreSQL migration",
    ]
    assert resumed["completed_steps"] == [
        "Step 1: Define core tables and primary key conventions"
    ]
    assert len(resumed["active_decisions"]) == 2
    decision_vals = [d["object_val"] for d in resumed["active_decisions"]]
    assert any("PostgreSQL with Drizzle ORM" in v for v in decision_vals)
    assert any("UUIDv7 for primary keys" in v for v in decision_vals)
    assert "[^src_dec_1]" in resumed["citations"]
    assert "[^src_dec_2]" in resumed["citations"]
    assert resumed["tokens_used"] < 350
    assert "PostgreSQL with Drizzle ORM" in resumed["packed_prompt"]
    assert "UUIDv7 for primary keys" in resumed["packed_prompt"]
