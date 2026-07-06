#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase42] Running focused tests..."
python -m pytest tests/unit/test_phase42_architecture_review_system_map.py -q
echo "[QRDS][Phase42] Running full suite..."
python -m pytest -q
echo "PHASE42_ARCHITECTURE_REVIEW_SYSTEM_MAP_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
