from datetime import datetime, timezone
from core.contracts import ClaimRecord, ClaimStatus, TrustTier
from core.schema import ShardManager
from core.okf_compiler import compile_namespace_okf
from core.forget import forget_target
from core.verifier import scan_shard_bytes


def test_role1_end_to_end_storage_and_verified_deletion(tmp_path):
    sm = ShardManager(root_dir=str(tmp_path))
    ns = "acme_corp/users/emp_042"
    ns_other = "acme_corp/users/emp_099"

    # 1. Append raw L2 message to filesystem
    raw_msg = "Hi team, I moved to BakerStreet221B last month."
    secret_str = "BakerStreet221B"
    b_start = raw_msg.find(secret_str)
    b_end = b_start + len(secret_str)

    sm.append_raw_source(ns, "src_01", "session_01.txt", raw_msg, "user", TrustTier.USER)

    # Seed separate shard for emp_099 to verify OpenViking shard isolation
    other_msg = "emp_099 works from TokyoHQ."
    sm.append_raw_source(ns_other, "src_99", "session_01.txt", other_msg, "user", TrustTier.USER)
    sm.insert_claim_with_lineage(
        ClaimRecord(
            claim_id="clm_99",
            namespace=ns_other,
            subject="emp_099",
            predicate="lives_in",
            object_val="TokyoHQ",
            status=ClaimStatus.ACTIVE,
            valid_from=datetime.now(timezone.utc).isoformat(),
            source_id="src_99",
            byte_start=other_msg.find("TokyoHQ"),
            byte_end=other_msg.find("TokyoHQ") + len("TokyoHQ"),
            okf_file="preferences.okf.md",
        ),
        [0.2] * 384,
    )
    compile_namespace_okf(sm, ns_other)

    # 2. Insert structured claim + 384-d dummy vector
    claim = ClaimRecord(
        claim_id="clm_01",
        namespace=ns,
        subject="emp_042",
        predicate="lives_in",
        object_val=secret_str,
        status=ClaimStatus.ACTIVE,
        valid_from=datetime.now(timezone.utc).isoformat(),
        source_id="src_01",
        byte_start=b_start,
        byte_end=b_end,
        okf_file="preferences.okf.md",
    )
    sm.insert_claim_with_lineage(claim, [0.1] * 384)
    compile_namespace_okf(sm, ns)

    shard_dir = sm.get_shard_dir(ns)
    other_shard_dir = sm.get_shard_dir(ns_other)

    # Confirm shard isolation before deletion
    assert scan_shard_bytes(other_shard_dir, [secret_str]) == 0
    assert (shard_dir / ".abstract.md").exists()
    assert (shard_dir / "preferences.okf.md").exists()

    # Confirm secret exists in raw bytes before deletion (in .sqlite, .okf.md, and session_01.txt)
    matches_before = scan_shard_bytes(shard_dir, [secret_str])
    assert matches_before >= 3

    # 3. Execute verified deletion
    receipt = forget_target(sm, ns, "lives_in")

    # 4. Assert 100% byte-level erasure across SQLite, WAL, FTS5, vec_claims, OKF, and raw source file
    assert receipt.byte_scan_matches == 0
    assert receipt.fts_rebuilt is True
    assert receipt.vacuum_completed is True
    assert len(receipt.suppression_hmacs) == 1

    # Confirm emp_099's shard was untouched
    assert scan_shard_bytes(other_shard_dir, ["TokyoHQ"]) >= 3

    print("\nVerified Deletion Receipt:", receipt.model_dump_json(indent=2))
