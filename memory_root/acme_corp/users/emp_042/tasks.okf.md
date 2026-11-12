---
okf_version: '0.2'
namespace: acme_corp/users/emp_042
task_id: payment_db_migration
status: in_progress
created_by_agent: agent2_executor
updated_at: '2026-11-12T20:49:34Z'
relied_on_claims:
- claim_042_loc_active
- claim_3f517cc9
- claim_c8de2689
sources:
- source_id: src_03fab7
  file_path: sources/session_20261112_204932_src_03fab7.txt
  trust_tier: 3
  origin: architect_session
- source_id: src_12
  file_path: sources/session_12.txt
  trust_tier: 4
  origin: user_session
- source_id: src_355a53
  file_path: sources/session_20261112_204932_src_355a53.txt
  trust_tier: 3
  origin: architect_session
active_decisions:
- claim_id: claim_042_loc_active
  predicate: lives_in
  object_val: Bengaluru
  citation: '[^src_12]'
- claim_id: claim_3f517cc9
  predicate: target_database
  object_val: PostgreSQL 16
  citation: '[^src_03fab7]'
- claim_id: claim_c8de2689
  predicate: primary_key_spec
  object_val: uuidv7
  citation: '[^src_355a53]'
---

# Task Handoff: payment_db_migration

## Goal
Payment service database migration from MongoDB to PostgreSQL 16 with uuidv7 keys.

## Completed Steps
- Step 1: DDL Schema generated
- Step 2: Write Python idempotent dual-write backfill script honoring active DB & key constraints

## Pending Steps
- (None)

## Active Decisions & Provenance
- lives_in: Bengaluru [^src_12] (claim: `claim_042_loc_active`)
- target_database: PostgreSQL 16 [^src_03fab7] (claim: `claim_3f517cc9`)
- primary_key_spec: uuidv7 [^src_355a53] (claim: `claim_c8de2689`)

## Open Questions
- (None)

## Evidence & Citations
[^src_03fab7]: sources/session_20261112_204932_src_03fab7.txt "Payment service migration will switch from MongoDB to PostgreSQL 16." (trust_tier=3)
[^src_12]: sources/session_12.txt "now live in Bengaluru" (trust_tier=4)
[^src_355a53]: sources/session_20261112_204932_src_355a53.txt "All primary keys in payment tables must use uuidv7." (trust_tier=3)
