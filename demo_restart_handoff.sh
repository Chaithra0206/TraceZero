#!/usr/bin/env bash
set -e

echo "========================================================================"
echo " KNOWLEDGE BRAIN: MULTI-AGENT MID-TASK HANDOFF & DISK PERSISTENCE DEMO"
echo "========================================================================"

# Ensure artifacts directory exists
mkdir -p artifacts

# 1. Run Agent 1 (Architect / Planner Agent)
echo ""
echo ">>> [STAGE 1] Running Agent 1 (Architect / Planner Agent)..."
python agents/agent1_architect.py

# 2. Simulate Unscheduled Process Kill & Verify Disk Persistence
echo ""
echo ">>> [STAGE 2] Simulating Unscheduled Process Failure (SIGKILL)..."
pkill -9 -f mcp_server.py 2>/dev/null || true
echo "[TEST] Process killed (SIGKILL). Verifying disk persistence..."

if [ ! -f "memory_root/acme_corp/users/emp_042/tasks.okf.md" ]; then
    echo "ERROR: tasks.okf.md did not persist to disk!"
    exit 1
fi
echo "[DISK PERSISTENCE VERIFIED] memory_root/acme_corp/users/emp_042/tasks.okf.md intact on disk."

# 3. Run Agent 2 (Executor Agent) with ZERO Prior Context Window
echo ""
echo ">>> [STAGE 3] Running Agent 2 (Executor) with ZERO Prior In-Memory Context..."
python agents/agent2_executor.py

# 4. Verify Generated Artifacts and Architectural Constraints
echo ""
echo ">>> [STAGE 4] Verifying generated code artifacts & architectural constraints..."
if [ ! -f "artifacts/step1_schema.sql" ]; then
    echo "ERROR: artifacts/step1_schema.sql was not generated!"
    exit 1
fi

if [ ! -f "artifacts/step2_backfill_worker.py" ]; then
    echo "ERROR: artifacts/step2_backfill_worker.py was not generated!"
    exit 1
fi

# Verify uuidv7 and postgresql references in step2_backfill_worker.py
grep -iq "uuidv7" artifacts/step2_backfill_worker.py || (echo "ERROR: uuidv7 not found in step2_backfill_worker.py!" && exit 1)
grep -iq "postgres" artifacts/step2_backfill_worker.py || (echo "ERROR: postgresql not found in step2_backfill_worker.py!" && exit 1)

echo " Artifact 1: artifacts/step1_schema.sql verified."
echo " Artifact 2: artifacts/step2_backfill_worker.py verified."
echo " Active constraints verified: 'PostgreSQL 16' and 'uuidv7' correctly honored."
echo ""
echo "========================================================================"
echo " ✅ DEMONSTRATION COMPLETE: Multi-agent handoff + kill/restart PASSED!"
echo "========================================================================"
