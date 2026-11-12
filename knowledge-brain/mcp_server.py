"""Root entrypoint for Knowledge Brain MCP server."""

import os
import sys

# Ensure knowledge-brain directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server.mcp_server import (
    api,
    explain,
    forget,
    handoff_create,
    handoff_get,
    history,
    mcp,
    quarantine_list,
    recall,
    remember,
    verify_deletion,
)

if __name__ == "__main__":
    if hasattr(mcp, "run"):
        mcp.run()

