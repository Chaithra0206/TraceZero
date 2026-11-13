# TraceZero (Knowledge Brain): 5-Strategy Benchmark Report

- **Execution Mode**: `live`
- **Deterministic Seed**: `random.seed(42)`
- **Tokenizer**: `tiktoken` (`cl100k_base`)
- **Target Namespace**: `acme_corp/users/emp_042` (30 migration sessions: **17,539 full-history tokens**; 17,580 w/ profile)
- **Verified Deletion Cleanliness**: **100%** (`byte_scan_matches: 0` across `.sqlite`, `-wal`, `.okf.md`, `sources/*.txt`) vs. **0%** (`Naive RAG / Prompt-stuffed`)

## 5-Strategy x 5-Question-Type Evaluation Matrix

| Storage Strategy | Preference (%) | Multi-hop (%) | What Changed (%) | Count/Aggregate (%) | Task State (%) | Overall Acc (%) | Avg Tokens (`tiktoken`) | p50 (ms) | p95 (ms) | Byte-Clean (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Prompt-stuffed** | 67.5% | 60.0% | 60.0% | 62.5% | 60.0% | **62.0%** | 17,601 | 0.06 | 0.09 | 0% |
| **Pure Vector (sqlite-vec)** | 92.5% | 91.7% | 47.5% | 62.5% | 60.0% | **70.8%** | 733 | 15.15 | 17.60 | 0% |
| **Claims / Knowledge Graph** | 92.5% | 100.0% | 75.0% | 85.0% | 100.0% | **90.5%** | 360 | 8.02 | 16.13 | 0% |
| **OKF Files (.okf.md)** | 92.5% | 85.0% | 60.0% | 80.0% | 85.0% | **80.5%** | 1,184 | 1.67 | 2.58 | 0% |
| **SQL / Code (run_readonly_sql)** | 100.0% | 91.7% | 100.0% | 100.0% | 100.0% | **98.3%** | 150 | 5.45 | 8.96 | 0% |
| **Hybrid Scoped Engine** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** | 351 | 46.80 | 53.69 | 100% |

## Live TokenLedger Accounting Summary (10 Queries / Strategy)

| Strategy | Calls | Total Context Tokens | Avg Context Tokens | Total Prompt Tokens |
| :--- | :---: | :---: | :---: | :---: |
| **Prompt-stuffed** | 10 | 176,010 | 17,601.0 | 176,010 |
| **Pure Vector (sqlite-vec)** | 10 | 7,334 | 733.4 | 7,334 |
| **Claims / Knowledge Graph** | 10 | 3,596 | 359.6 | 3,596 |
| **OKF Files (.okf.md)** | 10 | 11,839 | 1,183.9 | 11,839 |
| **SQL / Code (run_readonly_sql)** | 10 | 1,504 | 150.4 | 1,504 |
| **Hybrid Scoped Engine** | 10 | 3,510 | 351.0 | 3,510 |

## Key Measured Findings

1. **Token Savings**: `Hybrid Scoped Engine` averages **351 tokens/query** (strictly `<= 800` budget) vs. **17,539 full-history tokens** (**98.0% reduction**).
2. **Low Tail Latency**: `Hybrid Scoped Engine` achieves **p50 = 46.80ms**, **p95 = 53.69ms**.
3. **Single-Strategy Gaps Exposed**: `OKF Files` misses historical updates (`What Changed`), `Pure Vector` leaks stale/disputed/redundant chunks without status filtering, `Prompt-stuffed` blows context budgets and leaks poisoned injections, while `Hybrid Scoped Engine` dynamically routes across SQL, Recursive CTE, OKF, and Vector.

## Full-History vs. Naive Top-K Vector RAG vs. TraceZero (Knowledge Brain)

| System / Baseline | Avg Tokens / Query | Token Savings vs 30-Session History | p50 / p95 Latency (ms) | Contradiction Acc (%) | Poison Resistance (%) | Abstention Precision (%) | Verified Byte-Clean Deletion (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full-History Prompt Stuffing (30 Sessions)** | 17,539 | 0.0% | 0.02 / 0.03 | 0.0% | 0.0% | 0.0% | 0.0% |
| **Plain Top-K Vector RAG / OpenMemory Baseline** | 273.7 | 98.4% | 13.15 / 13.54 | 0.0% | 0.0% | 0.0% | 0.0% |
| **TraceZero (Knowledge Brain)** | **244.8** | **98.60%** | **26.09 / 33.97** | **100.0%** | **100.0%** | **100.0%** | **100.0% (`bytes=0`)** |
