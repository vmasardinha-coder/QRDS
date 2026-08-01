#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
echo "[QRDS][Phase40-HOTFIX] Verifying focused Phase 40 import/test..."
pytest -q tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py
echo "[QRDS][Phase40-HOTFIX] Running full suite..."
pytest -q
