#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase54] Running focused tests..."
python -m pytest tests/unit/test_phase54_shadow_replay_quality_bias_audit_research_only.py -q
echo "[QRDS][Phase54] Running full suite..."
python -m pytest -q
echo "PHASE54_SHADOW_REPLAY_QUALITY_BIAS_AUDIT_RESEARCH_ONLY_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "Shadow decision allowed: False"
echo "Decision layer allowed: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
