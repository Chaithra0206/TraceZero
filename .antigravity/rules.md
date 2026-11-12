# Role 4: Evaluation Harness, 30-Session Dataset & 5-Strategy Benchmark Rules

## Strict File Boundaries
- You may ONLY create or edit files inside:
  - `knowledge-brain/evals/`
  - `knowledge-brain/tests/`
  - `.antigravity/`
- You MUST NOT create or modify any files inside `knowledge-brain/core/` or `knowledge-brain/server/`.

## Determinism & Token Accounting
- All synthetic data generation and evaluation logic MUST use `random.seed(42)` for complete determinism.
- All LLM token counting MUST use `tiktoken.get_encoding("cl100k_base")`.

## Team Contract Signatures
All evaluation harnesses must code against these standard engine interfaces:
- `ingest_message(namespace: str, text: str, origin: str) -> list[str]`
- `recall_context(namespace: str, query: str, token_budget: int = 800) -> dict`
  - Returns `{status, packed_prompt, citations, tokens_used, latency_ms}`
- `forget_target(namespace: str, target: str) -> dict`
  - Returns deletion receipt dict including `byte_matches`
