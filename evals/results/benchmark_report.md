# TraceZero (Knowledge Brain): 5-Strategy Benchmark Report

- **Execution Mode**: `live`
- **Deterministic Seed**: `random.seed(42)`
- **Tokenizer**: `tiktoken` (`cl100k_base`)
- **Target Namespace**: `acme_corp/users/emp_042` (30 migration sessions: **17,263 full-history tokens**; 17,294 w/ profile)
- **Verified Deletion Cleanliness**: **100%** (`byte_scan_matches: 0` across `.sqlite`, `-wal`, `.okf.md`, `sources/*.txt`) vs. **0%** (`Naive RAG / Prompt-stuffed`)

## 5-Strategy x 5-Question-Type Evaluation Matrix

| Storage Strategy | Preference (%) | Multi-hop (%) | What Changed (%) | Count/Aggregate (%) | Task State (%) | Overall Acc (%) | Avg Tokens (`tiktoken`) | p50 (ms) | p95 (ms) | Byte-Clean (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Prompt-stuffed** | 67.5% | 60.0% | 60.0% | 62.5% | 60.0% | **62.0%** | 17,310 | 0.03 | 0.03 | 0% |
| **Pure Vector (sqlite-vec)** | 92.5% | 75.0% | 75.0% | 72.5% | 75.0% | **78.0%** | 377 | 35.29 | 41.93 | 0% |
| **Claims / Knowledge Graph** | 100.0% | 100.0% | 75.0% | 100.0% | 100.0% | **95.0%** | 233 | 1.50 | 2.62 | 0% |
| **OKF Files (.okf.md)** | 100.0% | 92.5% | 75.0% | 100.0% | 85.0% | **90.5%** | 725 | 0.10 | 0.13 | 0% |
| **SQL / Code (run_readonly_sql)** | 100.0% | 91.7% | 100.0% | 100.0% | 100.0% | **98.3%** | 146 | 0.42 | 0.50 | 0% |
| **Hybrid Scoped Engine** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** | 390 | 34.66 | 36.55 | 100% |

## Live TokenLedger Accounting Summary (10 Queries / Strategy)

| Strategy | Calls | Total Context Tokens | Avg Context Tokens | Total Prompt Tokens |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt-stuffed** | 10 | 173,100 | 17,310.0 | 173,100 |
| **Pure Vector (sqlite-vec)** | 10 | 3,772 | 377.2 | 3,772 |
| **Claims / Knowledge Graph** | 10 | 2,334 | 233.4 | 2,334 |
| **OKF Files (.okf.md)** | 10 | 7,246 | 724.6 | 7,246 |
| **SQL / Code (run_readonly_sql)** | 10 | 1,458 | 145.8 | 1,458 |
| **Hybrid Scoped Engine** | 10 | 3,904 | 390.4 | 3,904 |

## Key Measured Findings

1. **Token Savings**: `Hybrid Scoped Engine` averages **390 tokens/query** (strictly `<= 800` budget) vs. **17,263 full-history tokens** (**97.74% reduction**).
2. **Low Tail Latency**: `Hybrid Scoped Engine` achieves **p50 = 34.66ms**, **p95 = 36.55ms**.
3. **Single-Strategy Gaps Exposed**: `OKF Files` misses historical updates (`What Changed`), `Pure Vector` leaks stale/disputed/redundant chunks without status filtering, `Prompt-stuffed` blows context budgets and leaks poisoned injections, while `Hybrid Scoped Engine` dynamically routes across SQL, Recursive CTE, OKF, and Vector.

## Full-History vs. Naive Top-K Vector RAG vs. TraceZero (Knowledge Brain)

| System / Baseline | Avg Tokens / Query | Token Savings vs 30-Session History | p50 / p95 Latency (ms) | Contradiction Acc (%) | Poison Resistance (%) | Abstention Precision (%) | Verified Byte-Clean Deletion (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full-History Prompt Stuffing (30 Sessions)** | 17,263 | 0.0% | 0.01 / 0.02 | 0.0% | 0.0% | 0.0% | 0.0% |
| **Plain Top-K Vector RAG / OpenMemory Baseline** | 136.3 | 99.2% | 44.97 / 45.33 | 0.0% | 0.0% | 0.0% | 0.0% |
| **TraceZero (Knowledge Brain)** | **310.2** | **98.20%** | **5.93 / 34.29** | **100.0%** | **100.0%** | **100.0%** | **100.0% (`bytes=0`)** |
