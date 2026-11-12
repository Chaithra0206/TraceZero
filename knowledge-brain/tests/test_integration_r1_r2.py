from core import (
    ClaimStatus,
    MemoryStore,
    ingest_message,
    recall_context,
)


def test_role1_role2_full_pipeline_integration(tmp_path):
    store = MemoryStore(root_dir=str(tmp_path))
    ns = "acme_corp/users/emp_042"
    shard_dir = store.sm.get_shard_dir(ns)

    # 1. Ingest Fact V1 ("I live in Mangalore", origin="user")
    res_v1 = ingest_message(
        store=store,
        namespace=ns,
        text="I live in Mangalore.",
        origin="user",
        source_id="src_v1",
        session_id="session_01",
    )
    assert len(res_v1) == 1
    assert res_v1[0]["predicate"] == "lives_in"
    assert res_v1[0]["object_val"] == "Mangalore"
    assert res_v1[0]["status"] == ClaimStatus.ACTIVE.value

    okf_v1 = (shard_dir / "preferences.okf.md").read_text(encoding="utf-8")
    assert "Mangalore" in okf_v1
    assert "[^src_v1]" in okf_v1

    # 2. Ingest Update V2 ("I moved to Bengaluru", origin="user")
    res_v2 = ingest_message(
        store=store,
        namespace=ns,
        text="I moved to Bengaluru.",
        origin="user",
        source_id="src_v2",
        session_id="session_01",
    )
    assert len(res_v2) == 1
    assert res_v2[0]["predicate"] == "lives_in"
    assert res_v2[0]["object_val"] == "Bengaluru"
    assert res_v2[0]["status"] == ClaimStatus.ACTIVE.value

    with store.sm.get_connection(ns) as conn:
        row_v1 = conn.execute(
            "SELECT status, valid_to FROM claims_index WHERE claim_id = ?",
            (res_v1[0]["claim_id"],),
        ).fetchone()
        row_v2 = conn.execute(
            "SELECT status, valid_to FROM claims_index WHERE claim_id = ?",
            (res_v2[0]["claim_id"],),
        ).fetchone()
    assert row_v1["status"] == ClaimStatus.SUPERSEDED.value
    assert row_v1["valid_to"] is not None
    assert row_v2["status"] == ClaimStatus.ACTIVE.value

    # 3. Ingest Contradiction ("emp_042 lives in Mumbai", origin="doc")
    res_doc = ingest_message(
        store=store,
        namespace=ns,
        text="emp_042 lives in Mumbai.",
        origin="doc",
        source_id="src_doc",
        session_id="session_02",
    )
    assert len(res_doc) == 1
    assert res_doc[0]["predicate"] == "lives_in"
    assert res_doc[0]["object_val"] == "Mumbai"
    assert res_doc[0]["status"] in (
        ClaimStatus.DISPUTED.value,
        ClaimStatus.QUARANTINED.value,
    )

    # Confirm Bengaluru remains the sole active lives_in claim
    active_lives_in = store.get_active_claims_for_slot(ns, "emp_042", "lives_in")
    assert len(active_lives_in) == 1
    assert active_lives_in[0]["object_val"] == "Bengaluru"

    # 4. Recall "Where do I live?" -> Bengaluru with [^src_v2] citation within 800 tokens
    recall_ok = recall_context(store, ns, "Where do I live?", token_budget=800)
    assert recall_ok.status == "ok"
    assert recall_ok.tokens_used <= 800
    assert "Bengaluru" in recall_ok.packed_prompt
    assert "[^src_v2]" in recall_ok.packed_prompt
    assert "[^src_v2]" in recall_ok.citations
    assert "Mumbai" not in recall_ok.packed_prompt

    # 5. Recall "What is my passport number?" -> honest abstention
    recall_unknown = recall_context(store, ns, "What is my passport number?", token_budget=800)
    assert recall_unknown.status == "abstained"
    assert recall_unknown.packed_prompt == "I have no memory of that."

    # 6. Call store.forget(ns, "lives_in") -> 0 byte matches & subsequent recall abstains
    receipt = store.forget(ns, "lives_in")
    assert receipt.byte_scan_matches == 0
    assert receipt.is_zero_trace_verified is True

    recall_after_forget = recall_context(store, ns, "Where do I live?", token_budget=800)
    assert recall_after_forget.status == "abstained"
    assert recall_after_forget.packed_prompt == "I have no memory of that."
