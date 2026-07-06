#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"; PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"; export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase49] Running focused tests..."; python -m pytest tests/unit/test_phase49_risk_budget_framework_research_only.py -q
echo "[QRDS][Phase49] Running full suite..."; python -m pytest -q
echo "PHASE49_RISK_BUDGET_FRAMEWORK_RESEARCH_ONLY_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "Shadow decision allowed: False"
echo "Decision layer allowed: False"
echo "Allocation generated: False"
echo "Portfolio recommendation generated: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
