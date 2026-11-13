---
okf_version: '0.2'
namespace: acme_corp/users/emp_042
task_id: payment_migration
status: in_progress
created_by_agent: agent_1
updated_at: '2026-11-13T01:54:13Z'
relied_on_claims:
- claim_3f517cc9
- claim_c8de2689
- claim_04740bbb
- claim_ae428d73
sources:
- source_id: src_03fab7
  file_path: sources/session_20261112_204932_src_03fab7.txt
  trust_tier: 3
  origin: architect_session
- source_id: src_24f482
  file_path: sources/session_20261113_015157_src_24f482.txt
  trust_tier: 4
  origin: user
- source_id: src_355a53
  file_path: sources/session_20261112_204932_src_355a53.txt
  trust_tier: 3
  origin: architect_session
- source_id: src_840b49
  file_path: sources/session_20261113_015223_src_840b49.txt
  trust_tier: 4
  origin: user
active_decisions:
- claim_id: claim_3f517cc9
  predicate: target_database
  object_val: PostgreSQL 16
  citation: '[^src_03fab7]'
- claim_id: claim_c8de2689
  predicate: primary_key_spec
  object_val: uuidv7
  citation: '[^src_355a53]'
- claim_id: claim_04740bbb
  predicate: favorite_color
  object_val: electric indigo
  citation: '[^src_24f482]'
- claim_id: claim_ae428d73
  predicate: lives_in
  object_val: Bengaluru
  citation: '[^src_840b49]'
---

# Task Handoff: payment_migration

## Goal
Migrate payment service database from MongoDB to PostgreSQL 16 with uuidv7 primary keys.

## Completed Steps
- Provisioned PostgreSQL 16 staging cluster
- Verified uuidv7 schema generation

## Pending Steps
- Run dual-write shadow traffic
- Cut over production reads and writes to PostgreSQL 16

## Active Decisions & Provenance
- target_database: PostgreSQL 16 [^src_03fab7] (claim: `claim_3f517cc9`)
- primary_key_spec: uuidv7 [^src_355a53] (claim: `claim_c8de2689`)
- favorite_color: electric indigo [^src_24f482] (claim: `claim_04740bbb`)
- lives_in: Bengaluru [^src_840b49] (claim: `claim_ae428d73`)

## Open Questions
- Confirm rollback window duration with SRE

## Evidence & Citations
[^src_03fab7]: sources/session_20261112_204932_src_03fab7.txt "Payment service migration will switch from MongoDB to PostgreSQL 16." (trust_tier=3)
[^src_24f482]: sources/session_20261113_015157_src_24f482.txt "My favorite color is electric indigo and I live in Mangaluru." (trust_tier=4)
[^src_355a53]: sources/session_20261112_204932_src_355a53.txt "All primary keys in payment tables must use uuidv7." (trust_tier=3)
[^src_840b49]: sources/session_20261113_015223_src_840b49.txt "I moved to Bengaluru this week." (trust_tier=4)
