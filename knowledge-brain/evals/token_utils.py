"""Token counting utilities and live TokenLedger using tiktoken (cl100k_base)."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

_CACHE_DIR = Path(__file__).resolve().parent / "data" / ".tiktoken_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(_CACHE_DIR))

import tiktoken

_ENCODING = None


def _get_encoding() -> tiktoken.Encoding:
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    """Count exact tokens in text using cl100k_base encoding."""
    if not text:
        return 0
    return len(_get_encoding().encode(text))


def measure_prompt_payload(
    system_prompt: str, packed_context: str, user_query: str
) -> dict[str, int]:
    """Measure token breakdown and total payload for a prompt."""
    sys_tokens = count_tokens(system_prompt)
    ctx_tokens = count_tokens(packed_context)
    qry_tokens = count_tokens(user_query)
    total_tokens = sys_tokens + ctx_tokens + qry_tokens
    return {
        "system_tokens": sys_tokens,
        "context_tokens": ctx_tokens,
        "query_tokens": qry_tokens,
        "total_tokens": total_tokens,
    }


@dataclass
class TokenLedger:
    """Tracks running context_tokens, prompt_tokens, completion_tokens, and call_count on the fly."""

    name: str = "default"
    context_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    call_count: int = 0
    history: list[dict[str, int]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def avg_context_tokens(self) -> float:
        if self.call_count == 0:
            return 0.0
        return round(self.context_tokens / self.call_count, 1)

    @property
    def avg_prompt_tokens(self) -> float:
        if self.call_count == 0:
            return 0.0
        return round(self.prompt_tokens / self.call_count, 1)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "context_tokens": self.context_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "avg_context_tokens": self.avg_context_tokens,
            "avg_prompt_tokens": self.avg_prompt_tokens,
        }

    def format_line(self) -> str:
        return (
            f"[TokenLedger:{self.name}] calls={self.call_count} | "
            f"context_tokens={self.context_tokens:,} (avg={self.avg_context_tokens}) | "
            f"prompt_tokens={self.prompt_tokens:,} | "
            f"completion_tokens={self.completion_tokens:,} | "
            f"total_tokens={self.total_tokens:,}"
        )


def _extract_provider_usage(llm_response: Any) -> tuple[int | None, int | None]:
    """Extract (prompt_tokens, completion_tokens) from OpenAI, Anthropic, or Google GenAI responses."""
    if llm_response is None:
        return None, None

    # Dict-like response
    if isinstance(llm_response, dict):
        usage = llm_response.get("usage") or llm_response.get("usage_metadata") or {}
        if isinstance(usage, dict):
            p = (
                usage.get("prompt_tokens")
                or usage.get("input_tokens")
                or usage.get("prompt_token_count")
            )
            c = (
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or usage.get("candidates_token_count")
            )
            if p is not None or c is not None:
                return int(p or 0), int(c or 0)

    # OpenAI / Anthropic style: response.usage
    usage_obj = getattr(llm_response, "usage", None)
    if usage_obj is not None:
        p = getattr(usage_obj, "prompt_tokens", None)
        if p is None:
            p = getattr(usage_obj, "input_tokens", None)
        c = getattr(usage_obj, "completion_tokens", None)
        if c is None:
            c = getattr(usage_obj, "output_tokens", None)
        if p is not None or c is not None:
            return int(p or 0), int(c or 0)

    # Google GenAI style: response.usage_metadata
    usage_meta = getattr(llm_response, "usage_metadata", None)
    if usage_meta is not None:
        p = getattr(usage_meta, "prompt_token_count", None)
        if p is None:
            p = getattr(usage_meta, "input_tokens", None)
        c = getattr(usage_meta, "candidates_token_count", None)
        if c is None:
            c = getattr(usage_meta, "output_tokens", None)
        if p is not None or c is not None:
            return int(p or 0), int(c or 0)

    return None, None


def record_llm_or_context_usage(
    ledger: TokenLedger, packed_prompt: str, llm_response: Any = None
) -> dict[str, int]:
    """Record on-the-fly token usage into a TokenLedger.

    1. Weighs `packed_prompt` immediately before sending via `count_tokens(packed_prompt)`.
    2. If `llm_response` is provided (OpenAI, Anthropic, or Google GenAI), reads the exact
       input/output receipt from `response.usage` or `response.usage_metadata`; otherwise
       falls back to `count_tokens` so `--mock` works seamlessly.
    """
    ctx_tokens = count_tokens(packed_prompt)
    receipt_prompt, receipt_completion = _extract_provider_usage(llm_response)

    if receipt_prompt is not None:
        prompt_tokens = receipt_prompt
        completion_tokens = receipt_completion or 0
    else:
        prompt_tokens = ctx_tokens
        if isinstance(llm_response, str):
            completion_tokens = count_tokens(llm_response)
        else:
            completion_tokens = 0

    ledger.context_tokens += ctx_tokens
    ledger.prompt_tokens += prompt_tokens
    ledger.completion_tokens += completion_tokens
    ledger.call_count += 1

    entry = {
        "call_index": ledger.call_count,
        "context_tokens": ctx_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    ledger.history.append(entry)
    return entry
