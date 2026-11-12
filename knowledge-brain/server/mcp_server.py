"""MCP Server exposing Knowledge Brain tools via Model Context Protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None

from server.api import KnowledgeBrainAPI


api = KnowledgeBrainAPI()

if FastMCP is not None:
    mcp = FastMCP("knowledge-brain")
else:
    # Fallback dummy class if running in an environment without mcp package
    class FallbackMCP:
        def __init__(self, name: str):
            self.name = name
        def tool(self):
            def decorator(fn):
                return fn
            return decorator
        def run(self):
            pass
    mcp = FallbackMCP("knowledge-brain")


@mcp.tool()
def remember(
    namespace: str,
    text: str,
    origin: str = "user",
    session_id: Optional[str] = None,
) -> str:
    """Ingest raw natural language message, extracting verified atomic claims."""
    claims = api.remember(namespace=namespace, text=text, origin=origin, session_id=session_id)
    return json.dumps(claims, indent=2)


@mcp.tool()
def recall(
    namespace: str,
    query: str,
    token_budget: int = 800,
) -> str:
    """Recall scoped context across L0 Abstract, L1 Triples, and L2 byte spans."""
    res = api.recall(namespace=namespace, query=query, token_budget=token_budget)
    return json.dumps(res.model_dump(), indent=2)


@mcp.tool()
def forget(
    namespace: str,
    target: str,
) -> str:
    """Purge target facts across Payload, Control, and Semantic planes."""
    receipt = api.forget(namespace=namespace, target=target)
    return json.dumps(receipt.model_dump(), indent=2)


@mcp.tool()
def verify_deletion(
    namespace: str,
    target_val: str,
) -> str:
    """Verify physical zero-byte presence and probe abstention for deleted memory."""
    details = api.verify_deletion(namespace=namespace, target_val=target_val)
    return json.dumps(details, indent=2)


@mcp.tool()
def explain(
    namespace: str,
    claim_id: str,
) -> str:
    """Retrieve full provenance, raw byte slice, and trust lineage for a claim."""
    data = api.explain(namespace=namespace, claim_id=claim_id)
    return json.dumps(data, indent=2)


@mcp.tool()
def history(
    namespace: str,
    subject: str,
    predicate: str,
) -> str:
    """Inspect temporal progression of a subject-predicate pair."""
    records = api.history(namespace=namespace, subject=subject, predicate=predicate)
    return json.dumps(records, indent=2)


@mcp.tool()
def quarantine_list(
    namespace: str,
) -> str:
    """List all quarantined or disputed claims in a namespace."""
    items = api.quarantine_list(namespace=namespace)
    return json.dumps(items, indent=2)


@mcp.tool()
def handoff_create(
    namespace: str,
    task_goal: str,
    completed_steps: List[str],
    pending_steps: List[str],
    blocked_steps: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    decisions: Optional[Dict[str, str]] = None,
) -> str:
    """Generate tasks.okf.md handoff state for cross-agent resumption."""
    packet = api.handoff_create(
        namespace=namespace,
        task_goal=task_goal,
        completed_steps=completed_steps,
        pending_steps=pending_steps,
        blocked_steps=blocked_steps,
        constraints=constraints,
        decisions=decisions,
    )
    return json.dumps(packet.model_dump(), indent=2)


@mcp.tool()
def handoff_get(
    namespace: str,
) -> str:
    """Restore state from tasks.okf.md without raw chat history."""
    packet = api.handoff_get(namespace=namespace)
    return json.dumps(packet.model_dump(), indent=2)


if __name__ == "__main__":
    if hasattr(mcp, "run"):
        mcp.run()

