from datetime import datetime, timezone
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
