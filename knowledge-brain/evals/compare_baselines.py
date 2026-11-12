"""Compare Knowledge Brain against standard prompt-stuffed and naive vector baselines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tiktoken

from core.handoff import handoff_get
from core.retrieval import count_tokens, get_tokenizer, recall_context
from evals.seed_30_sessions import SESSION_PROMPTS, seed_30_sessions


def evaluate_baselines(memory_root: Path, namespace: str = "acme/users/emp_042") -> Dict[str, Any]:
    """Calculate token footprint and efficiency metrics across memory baselines."""
    conn, shard_dir, _ = seed_30_sessions(memory_root, namespace)
    enc = get_tokenizer()

    # 1. Full Raw Chat History Baseline (Prompt-stuffed)
    raw_history_text = "\n\n".join(
        f"User: {text}\nAssistant: Understood." for _, text in SESSION_PROMPTS
    )
    raw_history_tokens = len(enc.encode(raw_history_text))

    # 2. Pure Vector RAG Baseline (top-5 naive text chunks)
    # Naive RAG dumps top-5 raw text session chunks (~150-250 tokens per chunk)
    vector_rag_chunks = [text for _, text in SESSION_PROMPTS[-5:]]
    vector_rag_text = "\n---\n".join(vector_rag_chunks)
    vector_rag_tokens = len(enc.encode(vector_rag_text))

    # 3. Knowledge Brain Tiered Recall
    recall_res = recall_context(conn, shard_dir, namespace, "What database and architecture decisions did we make?")
    kb_recall_tokens = recall_res.tokens_used

    # 4. Knowledge Brain Handoff Packet
    handoff_pkt = handoff_get(shard_dir, namespace)
    handoff_summary = f"Goal: {handoff_pkt.task_goal}\nCompleted: {', '.join(handoff_pkt.completed_steps)}\nPending: {', '.join(handoff_pkt.pending_steps)}\nDecisions: {handoff_pkt.active_decisions}"
    kb_handoff_tokens = len(enc.encode(handoff_summary))

    token_savings_pct = (1.0 - (kb_handoff_tokens / raw_history_tokens)) * 100.0

    return {
        "raw_history_tokens": raw_history_tokens,
        "vector_rag_tokens": vector_rag_tokens,
        "kb_recall_tokens": kb_recall_tokens,
        "kb_handoff_tokens": kb_handoff_tokens,
        "token_savings_pct": token_savings_pct,
    }


if __name__ == "__main__":
    import tempfile
    from core.schema import close_all_shards
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        res = evaluate_baselines(Path(tmpdir))
        close_all_shards()
        print("Baseline Comparison Metrics:")
        print(f"  - Full 30-Session Chat History: {res['raw_history_tokens']} tokens")
        print(f"  - Naive Vector RAG (5 chunks):   {res['vector_rag_tokens']} tokens")
        print(f"  - KB Tiered Recall Context:      {res['kb_recall_tokens']} tokens")
        print(f"  - KB Cross-Agent Handoff Packet: {res['kb_handoff_tokens']} tokens")
        print(f"  - Handoff Token Savings:         {res['token_savings_pct']:.2f}%")
