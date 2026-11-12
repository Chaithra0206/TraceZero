"""Knowledge Brain server wrapper for mcp_server."""

import importlib.util
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

target_file = repo_root / "mcp_server.py"
spec = importlib.util.spec_from_file_location("root_mcp_server", target_file)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

create_mcp_server = mod.create_mcp_server
mcp = mod.mcp
main = mod.main

__all__ = [
    "create_mcp_server",
    "mcp",
    "main",
]

if __name__ == "__main__":
    main()
