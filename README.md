# TraceZero — Knowledge Brain (PS-06)

**Knowledge Brain: Memory That Knows What to Keep and When to Forget** is an enterprise-grade 3-plane agent memory architecture that eliminates prompt-stuffing bloat, enforces cryptographic zero-byte forgetting, and enables cross-agent handoffs with >95% token savings.

---

## Architecture (3-Plane Enterprise Design)

```
                    ┌────────────────────────────────────────────────────────┐
                    │               3-PLANE ENTERPRISE DESIGN                │
                    └────────────────────────────────────────────────────────┘
                                                │
         ┌──────────────────────────────────────┼──────────────────────────────────────┐
         ▼                                      ▼                                      ▼
┌─────────────────────────┐           ┌─────────────────────────┐            ┌─────────────────────────┐
│     PAYLOAD PLANE       │           │ CONTROL & LINEAGE PLANE │            │     SEMANTIC PLANE      │
│  (OpenViking + OKF v0.2)│           │ (Per-Shard index.sqlite)│            │  (sqlite-vec0 + FTS5)   │
├─────────────────────────┤           ├─────────────────────────┤            ├─────────────────────────┤
│ • .abstract.md (L0)     │           │ • WAL Mode + PRAGMA     │            │ • vec_claims (vec0)     │
│ • preferences.okf.md    │           │   secure_delete = ON    │            │   (384-dim BGE-small)   │
│ • decisions.okf.md      │           │ • sources_index (SHA256)│            │ • fts_claims (FTS5)     │
│ • tasks.okf.md          │           │ • claims_index (triples)│            │ • Strict Abstention Gate│
│ • notes.okf.md          │           │ • lineage_index         │            │   (No match & d > 0.80) │
│ • sources/*.txt (L2 raw)│           │ • suppression_hashes    │            │ • Zero prompt leakage   │
└─────────────────────────┘           └─────────────────────────┘            └─────────────────────────┘
```

1. **Payload Plane (OpenViking Tier L0 + Google OKF v0.2 Markdown Filesystem)**:
   - Shard layout: `memory_root/{namespace}/` (e.g., `memory_root/acme/users/emp_042/`).
   - `.abstract.md`: OpenViking Tier L0 (~50–150 tokens) identity and preferences summary.
   - `preferences.okf.md`, `decisions.okf.md`, `tasks.okf.md`, `notes.okf.md`: Tier L1 Google OKF v0.2 Markdown files with YAML frontmatter (`okf_version: "0.2"`) and `[^source_id]` provenance footnotes.
   - `sources/session_XX.txt`: Tier L2 immutable raw natural language log files with `os.fsync()`. **Zero bulk natural language paragraphs are stored in SQLite cells.**
2. **Control & Lineage Plane (`index.sqlite` per shard)**:
   - SQLite in `WAL` mode with `PRAGMA secure_delete = ON; PRAGMA foreign_keys = ON;`.
   - Tables: `sources_index`, `entity_aliases`, `claims_index`, `lineage_index`, `suppression_hashes`.
   - 24 registered predicates with single/multi cardinality, storage tier routing, and trust tiers (`user: 3`, `tool: 2`, `doc: 1`, `web: 1`).
3. **Semantic Plane (`sqlite-vec` + `FTS5`)**:
   - `vec_claims USING vec0(embedding float[384])` with local `fastembed` (`BAAI/bge-small-en-v1.5`).
   - `fts_claims USING fts5(subject, predicate, object_val)`.
   - Strict **Abstention Gate**: If no active keyword/predicate match and best distance `> 0.80`, returns `"I have no memory of that."` with `0` tokens used.

---

## Directory Layout

```
TraceZero/
├── knowledge-brain/
│   ├── core/
│   │   ├── contracts.py       # PREDICATE_REGISTRY (24 predicates), Pydantic v2 schemas
│   │   ├── predicates.py      # Cardinality & target OKF mapping helpers
│   │   ├── schema.py          # SQLite WAL, secure_delete, sqlite-vec DDL loader
│   │   ├── okf_compiler.py    # Generates .abstract.md & *.okf.md with footnotes
│   │   ├── policy.py          # Injection detection, UTF-8 byte span check, HMAC hashes
│   │   ├── ingest.py          # Ingests raw logs, extracts atomic claims, updates indexes
│   │   ├── retrieval.py       # Deterministic router, abstention gate, token budgeting
│   │   ├── forget.py          # Raw disk redaction, secure_delete, VACUUM, receipt signing
│   │   ├── verifier.py        # Physical raw byte scanner & 10 paraphrase probes
│   │   └── handoff.py         # tasks.okf.md writer and parser for agent resumption
│   ├── server/
│   │   ├── api.py             # High-level Python API (KnowledgeBrainAPI)
│   │   └── mcp_server.py      # FastMCP tools (remember, recall, forget, verify, handoff...)
│   ├── evals/
│   │   ├── run_all_verifications.py # 10-check automated benchmark runner
│   │   ├── seed_30_sessions.py      # Seeds 30 realistic engineering sessions
│   │   ├── compare_baselines.py     # Measures token savings vs. raw history
│   │   └── run_5_strategies.py      # 5-strategy storage benchmark table
│   ├── tests/
│   │   └── test_knowledge_brain.py  # Complete pytest test suite (11 tests)
│   ├── cli.py                 # Interactive & one-line manual testing console
│   └── mcp_server.py          # Standalone MCP server entrypoint
├── pytest.cmd                 # Pytest runner wrapper
├── python3.cmd                # Python 3 runner wrapper
└── README.md
```

---

## Running Verifications & Tests

### 1. Run the Full 10-Check Verification Suite & Benchmark Table
```powershell
cd knowledge-brain
.\python3.cmd -m evals.run_all_verifications
```

### 2. Run the Unit & Integration Test Suite
```powershell
cd knowledge-brain
.\pytest.cmd -v -s
```

### 3. Interactive Manual Testing Console
```powershell
cd knowledge-brain
.\python3.cmd cli.py
```

### 4. Run Knowledge Brain MCP Server
```powershell
cd knowledge-brain
.\python3.cmd mcp_server.py
```
Exposes tools via the Model Context Protocol:
- `remember(namespace, text, origin)`
- `recall(namespace, query, token_budget)`
- `forget(namespace, target)`
- `verify_deletion(namespace, target_val)`
- `explain(namespace, claim_id)`
- `history(namespace, subject, predicate)`
- `quarantine_list(namespace)`
- `handoff_create(namespace, task_goal, ...)`
- `handoff_get(namespace)`
