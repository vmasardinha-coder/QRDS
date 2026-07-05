#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase40 hygiene verify] Running focused Phase 40 tests..."
python -m pytest tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py
echo "[QRDS][Phase40 hygiene verify] Running full suite..."
python -m pytest
cd "$ROOT_DIR"
if git status --porcelain | grep -E '^\?\? qrds_phase(39|40).*\.sh$' >/tmp/qrds_phase40_hygiene_untracked.txt; then
  echo "[QRDS][Phase40 hygiene verify][NEEDS_REVIEW] Root QRDS scripts still untracked:"
  cat /tmp/qrds_phase40_hygiene_untracked.txt
  exit 3
fi
echo "PHASE40_HOTFIX_REPO_HYGIENE_UNTRACKED_SCRIPT_CLEANUP_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "canonical_data_writes: 0"
