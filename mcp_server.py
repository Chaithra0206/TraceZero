"""Knowledge Brain MCP Server.

Exposes Knowledge Brain's auditable, temporal, provenance-backed memory layer
as Model Context Protocol (MCP) tools for Claude Code, Gemini CLI, Antigravity,
and other agentic frameworks over stdio or SSE/HTTP.

Available Tools:
1. remember: Ingest new facts, extract claims, update sources & OKF files.
2. recall: 3-tier memory recall (L0 abstract, L1 claims, L2 quotes) or honest abstention.
3. explain: Byte-accurate source quote retrieval from raw sources.
4. history: Full temporal timeline of active, superseded, and disputed claims.
5. forget: Cryptographic unlearning with byte redaction and secure SQLite vacuum.
6. verify_deletion: Verification proving zero byte leakage and 100% probe abstention.
7. quarantine_list: Inspect intercepted prompt injections and untrusted inputs.
8. confirm: Confirm or reject a quarantined or disputed claim.
9. handoff_create: Create an OKF v0.2 cross-agent task handoff packet.
10. handoff_get: Read and verify an OKF v0.2 task handoff packet for staleness.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root and knowledge-brain are in sys.path
repo_root = Path(__file__).resolve().parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
kb_root = repo_root / "knowledge-brain"
if str(kb_root) not in sys.path:
    sys.path.insert(0, str(kb_root))

from mcp.server.fastmcp import FastMCP
from core import bridge


def create_mcp_server(
    name: str = "KnowledgeBrain",
    host: str = "127.0.0.1",
    port: int = 8765,
) -> FastMCP:
    """Instantiate and configure the Knowledge Brain FastMCP server with 9 tools."""
    mcp = FastMCP(
        name=name,
        instructions=(
            "Knowledge Brain is an auditable, temporal memory layer for AI agents. "
            "Use 'remember' to record facts, 'recall' for 3-tier memory retrieval with honest abstention, "
            "'explain' for source byte provenance, 'history' for temporal lineage, "
            "'forget' for cryptographic unlearning, 'verify_deletion' to confirm zero leakage, "
            "'quarantine_list' for prompt injection inspection, and 'handoff_create' / 'handoff_get' "
            "for cross-agent task handoffs."
        ),
        host=host,
        port=port,
    )

    @mcp.tool()
    def remember(namespace: str, text: str, origin: str = "agent_interaction") -> Dict[str, Any]:
        """Ingest new information into Knowledge Brain.

        Appends to raw sources/, extracts claims into index.sqlite, and updates .okf.md.
        If prompt injection is detected, the claim is safely quarantined.

        Args:
            namespace: Memory shard namespace (e.g. 'acme_corp/users/emp_042').
            text: Statement, observation, or interaction text to remember.
            origin: Ingestion source origin (e.g. 'user_session', 'external_untrusted').
        """
        return bridge.remember(namespace=namespace, text=text, origin=origin)

    @mcp.tool()
    def recall(namespace: str, query: str, token_budget: int = 800) -> Dict[str, Any]:
        """Retrieve 3-tier memory payload (L0 abstract, L1 claims, L2 quotes) or honestly abstain.

        If no active match passes confidence or the concept has been suppressed/forgotten,
        returns status='abstained' and answer_hint='I have no memory of that.'

        Args:
            namespace: Memory shard namespace.
            query: Question, keyword, or concept to recall.
            token_budget: Maximum tokens allocated for L0+L1+L2 response packing.
        """
        return bridge.recall(namespace=namespace, query=query, token_budget=token_budget)

    @mcp.tool()
    def explain(namespace: str, claim_id: str) -> Dict[str, Any]:
        """Retrieve exact byte-accurate provenance quote and metadata by seeking in raw source file.

        Args:
            namespace: Memory shard namespace.
            claim_id: Unique claim identifier to audit.
        """
        return bridge.explain(namespace=namespace, claim_id=claim_id)

    @mcp.tool()
    def history(namespace: str, subject: str, predicate: str) -> List[Dict[str, Any]]:
        """Return the chronological timeline of all claims (active, superseded, disputed).

        Args:
            namespace: Memory shard namespace.
            subject: Entity identifier (e.g. 'emp_042').
            predicate: Attribute/relationship (e.g. 'lives_in', 'preferred_db').
        """
        return bridge.history(namespace=namespace, subject=subject, predicate=predicate)

    @mcp.tool()
    def forget(namespace: str, target: str) -> Dict[str, Any]:
        """Cryptographically unlearn target information.

        Redacts exact byte spans in raw source files with [REDACTED_BY_USER], removes claims
        from index.sqlite, inserts an HMAC into suppression_hashes, runs PRAGMA secure_delete=ON
        and VACUUM, and verifies 0 byte occurrences remain across files and SQLite.

        Args:
            namespace: Memory shard namespace.
            target: Target key, claim ID, or sensitive text to permanently erase.
        """
        return bridge.forget(namespace=namespace, target=target)

    @mcp.tool()
    def verify_deletion(namespace: str, target: str) -> Dict[str, Any]:
        """Verify permanent unlearning and deletion compliance.

        Verifies 0 raw byte matches in index.sqlite, 0 matches in sources/, confirms HMAC suppression
        presence, and runs 10 probe queries to verify 100% honest abstention.

        Args:
            namespace: Memory shard namespace.
            target: Deleted term or entity to verify.
        """
        return bridge.verify_deletion(namespace=namespace, target=target)

    @mcp.tool()
    def quarantine_list(namespace: str) -> List[Dict[str, Any]]:
        """List all quarantined claims intercepted by prompt injection or untrusted origin filters.

        Args:
            namespace: Memory shard namespace.
        """
        return bridge.quarantine_list(namespace=namespace)

    @mcp.tool()
    def confirm(namespace: str, claim_id: str, action: str = "approve") -> Dict[str, Any]:
        """Confirm (approve) or reject a quarantined or disputed claim.

        Args:
            namespace: Memory shard namespace.
            claim_id: Claim identifier to promote or reject.
            action: 'approve' to promote to active, or 'reject' to permanently remove.
        """
        return bridge.confirm_quarantine(namespace=namespace, claim_id=claim_id, action=action)

    @mcp.tool()
    def handoff_create(
        namespace: str,
        task_id: str,
        goal: str,
        completed_steps: List[str],
        pending_steps: List[str],
        open_questions: List[str],
        created_by_agent: str = "agent_1",
    ) -> Dict[str, Any]:
        """Create a Google Open Knowledge Format (OKF v0.2) cross-agent task handoff packet.

        Queries active claims from index.sqlite, compiles tasks.okf.md with YAML frontmatter,
        and tracks token compression compared to total raw source history.

        Args:
            namespace: Memory shard namespace.
            task_id: Unique task identifier.
            goal: Overarching goal of the task.
            completed_steps: List of completed milestones.
            pending_steps: List of remaining steps.
            open_questions: List of unresolved queries.
            created_by_agent: Identity of the handing-off agent.
        """
        return bridge.handoff_create(
            namespace=namespace,
            task_id=task_id,
            goal=goal,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            open_questions=open_questions,
            created_by_agent=created_by_agent,
        )

    @mcp.tool()
    def handoff_get(namespace: str, task_id: str) -> Dict[str, Any]:
        """Read and parse an OKF v0.2 task handoff packet, checking relied-upon claims for staleness.

        Args:
            namespace: Memory shard namespace.
            task_id: Task identifier.
        """
        return bridge.handoff_get(namespace=namespace, task_id=task_id)

    return mcp


# Module-level instance for direct imports
mcp = create_mcp_server()


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Brain MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for SSE transport (default: 8765)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host for SSE transport (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    server = create_mcp_server(name="KnowledgeBrain", host=args.host, port=args.port)
    if args.transport == "sse":
        print(f"Starting Knowledge Brain MCP Server on http://{args.host}:{args.port}/sse", file=sys.stderr)
        server.run(transport="sse")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
