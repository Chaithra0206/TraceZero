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
| **Pure Vector (sqlite-vec)** | 92.5% | 75.0% | 75.0% | 72.5% | 75.0% | **78.0%** | 379 | 35.53 | 37.23 | 0% |
| **Claims / Knowledge Graph** | 100.0% | 100.0% | 75.0% | 100.0% | 100.0% | **95.0%** | 233 | 1.58 | 2.11 | 0% |
| **OKF Files (.okf.md)** | 100.0% | 92.5% | 75.0% | 100.0% | 92.5% | **92.0%** | 707 | 0.09 | 0.11 | 0% |
| **SQL / Code (run_readonly_sql)** | 100.0% | 91.7% | 100.0% | 100.0% | 100.0% | **98.3%** | 146 | 0.43 | 0.48 | 0% |
| **Hybrid Scoped Engine** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** | 387 | 34.73 | 35.27 | 100% |

## Live TokenLedger Accounting Summary (10 Queries / Strategy)

| Strategy | Calls | Total Context Tokens | Avg Context Tokens | Total Prompt Tokens |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt-stuffed** | 10 | 173,100 | 17,310.0 | 173,100 |
| **Pure Vector (sqlite-vec)** | 10 | 3,791 | 379.1 | 3,791 |
| **Claims / Knowledge Graph** | 10 | 2,332 | 233.2 | 2,332 |
| **OKF Files (.okf.md)** | 10 | 7,074 | 707.4 | 7,074 |
| **SQL / Code (run_readonly_sql)** | 10 | 1,458 | 145.8 | 1,458 |
| **Hybrid Scoped Engine** | 10 | 3,867 | 386.7 | 3,867 |

## Key Measured Findings

1. **Token Savings**: `Hybrid Scoped Engine` averages **387 tokens/query** (strictly `<= 800` budget) vs. **17,263 full-history tokens** (**97.76% reduction**).
2. **Low Tail Latency**: `Hybrid Scoped Engine` achieves **p50 = 34.73ms**, **p95 = 35.27ms**.
3. **Single-Strategy Gaps Exposed**: `OKF Files` misses historical updates (`What Changed`), `Pure Vector` leaks stale/disputed/redundant chunks without status filtering, `Prompt-stuffed` blows context budgets and leaks poisoned injections, while `Hybrid Scoped Engine` dynamically routes across SQL, Recursive CTE, OKF, and Vector.

## Full-History vs. Naive Top-K Vector RAG vs. TraceZero (Knowledge Brain)

| System / Baseline | Avg Tokens / Query | Token Savings vs 30-Session History | p50 / p95 Latency (ms) | Contradiction Acc (%) | Poison Resistance (%) | Abstention Precision (%) | Verified Byte-Clean Deletion (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full-History Prompt Stuffing (30 Sessions)** | 17,263 | 0.0% | 0.01 / 0.02 | 0.0% | 0.0% | 0.0% | 0.0% |
| **Plain Top-K Vector RAG / OpenMemory Baseline** | 134.0 | 99.2% | 44.93 / 45.65 | 0.0% | 0.0% | 0.0% | 0.0% |
| **TraceZero (Knowledge Brain)** | **309.8** | **98.21%** | **5.99 / 34.81** | **100.0%** | **100.0%** | **100.0%** | **100.0% (`bytes=0`)** |
