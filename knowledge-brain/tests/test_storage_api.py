from datetime import datetime, timezone
import pytest
from core.contracts import ClaimRecord, ClaimStatus, TrustTier
from core.storage_api import MemoryStore


def test_multihop_graph_and_suppression_gate(tmp_path):
    store = MemoryStore(root_dir=str(tmp_path))
    ns = "acme_corp/users/emp_042"
    now = datetime.now(timezone.utc).isoformat()

    raw = "emp_042 works on project_atlas. project_atlas uses postgresql. My secret pin is 998877."
    store.save_source(ns, "src_1", "session_01.txt", raw, "user", TrustTier.USER)

    # Hop 1: emp_042 -> works_on -> project_atlas
    store.store_claim(ClaimRecord(
        claim_id="c1", namespace=ns, subject="emp_042", predicate="works_on",
        object_val="project_atlas", valid_from=now, source_id="src_1", byte_start=0, byte_end=30
    ))
    # Hop 2: project_atlas -> uses_db -> postgresql
    store.store_claim(ClaimRecord(
        claim_id="c2", namespace=ns, subject="project_atlas", predicate="uses_db",
        object_val="postgresql", valid_from=now, source_id="src_1", byte_start=32, byte_end=61
    ))
    # Secret claim to test deletion + suppression
    store.store_claim(ClaimRecord(
        claim_id="c3", namespace=ns, subject="emp_042", predicate="secret_pin",
        object_val="998877", valid_from=now, source_id="src_1", byte_start=80, byte_end=86
    ))

    # 1. Test 2-hop graph traversal (c1 + c3 at hop 1, c2 at hop 2)
    hops = store.query_graph_multihop(ns, "emp_042", max_hops=2)
    assert len(hops) == 3
    assert any(h["hop"] == 2 and h["object_val"] == "postgresql" for h in hops)

    # 2. Delete secret_pin and verify byte scan == 0
    receipt = store.forget(ns, "998877")
    assert receipt.byte_scan_matches == 0

    # 3. Try to re-learn the deleted fact -> must be blocked by suppression HMAC!
    relearned = store.store_claim(ClaimRecord(
        claim_id="c4", namespace=ns, subject="emp_042", predicate="secret_pin",
        object_val="998877", valid_from=now, source_id="src_1", byte_start=0, byte_end=6
    ))
    assert relearned is False


def test_history_explain_quarantine_and_readonly_sql(tmp_path):
    store = MemoryStore(root_dir=str(tmp_path))
    ns = "acme_corp/users/emp_042"
    shard_dir = store.sm.get_shard_dir(ns)

    raw_user = "I live in Mangalore."
    raw_doc = "emp_042 lives in Bengaluru."
    store.save_source(ns, "src_u1", "session_01.txt", raw_user, "user", TrustTier.USER)
    store.save_source(ns, "src_d1", "doc_01.txt", raw_doc, "doc", TrustTier.DOC_WEB)

    # Active user claim
    store.store_claim(ClaimRecord(
        claim_id="clm_u1",
        namespace=ns,
        subject="emp_042",
        predicate="lives_in",
        object_val="Mangalore",
        status=ClaimStatus.ACTIVE,
        valid_from="2026-11-13T01:00:00Z",
        source_id="src_u1",
        byte_start=0,
        byte_end=len(raw_user),
    ))

    # Quarantined doc claim for single-valued lives_in predicate
    store.store_claim(ClaimRecord(
        claim_id="clm_d1",
        namespace=ns,
        subject="emp_042",
        predicate="lives_in",
        object_val="Bengaluru",
        status=ClaimStatus.QUARANTINED,
        valid_from="2026-11-13T02:00:00Z",
        source_id="src_d1",
        byte_start=0,
        byte_end=len(raw_doc),
    ))

    # 1. explain_claim
    explained = store.explain_claim(ns, "clm_u1")
    assert explained["claim_id"] == "clm_u1"
    assert explained["origin"] == "user"
    assert explained["trust_tier"] == int(TrustTier.USER)
    assert explained["exact_quote"] == "I live in Mangalore."

    # 2. list_quarantined
    quarantined = store.list_quarantined(ns)
    assert len(quarantined) == 1
    assert quarantined[0]["claim_id"] == "clm_d1"
    assert quarantined[0]["exact_quote"] == "emp_042 lives in Bengaluru."

    # 3. confirm_quarantined_claim -> promotes clm_d1 to ACTIVE and supersedes clm_u1
    confirmed = store.confirm_quarantined_claim(ns, "clm_d1")
    assert confirmed is True
    assert len(store.list_quarantined(ns)) == 0

    okf_content = (shard_dir / "preferences.okf.md").read_text(encoding="utf-8")
    assert "Bengaluru" in okf_content
    assert "Mangalore" not in okf_content

    # 4. get_claim_history -> returns both superseded and active claims in chronological order
    history = store.get_claim_history(ns, "emp_042", predicate="lives_in")
    assert len(history) == 2
    assert history[0]["claim_id"] == "clm_u1"
    assert history[0]["status"] == ClaimStatus.SUPERSEDED.value
    assert history[0]["valid_to"] is not None
    assert history[1]["claim_id"] == "clm_d1"
    assert history[1]["status"] == ClaimStatus.ACTIVE.value

    # 5. run_readonly_sql
    rows = store.run_readonly_sql(
        ns,
        "SELECT status, COUNT(*) AS cnt FROM claims_index GROUP BY status ORDER BY status ASC",
    )
    status_counts = {r["status"]: r["cnt"] for r in rows}
    assert status_counts == {"active": 1, "superseded": 1}

    with pytest.raises(ValueError):
        store.run_readonly_sql(ns, "DELETE FROM claims_index")
