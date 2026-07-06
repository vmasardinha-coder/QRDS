#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase46] Running focused tests..."
python -m pytest tests/unit/test_phase46_shadow_journal_schema_integrated_repo_hygiene.py -q
echo "[QRDS][Phase46] Running full suite..."
python -m pytest -q
cd "$ROOT_DIR"
if git status --porcelain | grep -E '^\?\? qrds_sprint_4.*\.sh$|^\?\? qrds_phase4.*hotfix.*\.sh$' >/tmp/qrds_phase46_untracked.txt; then
  echo "[QRDS][Phase46][NEEDS_REVIEW] Loose installer/hotfix scripts still untracked:"
  cat /tmp/qrds_phase46_untracked.txt
  exit 3
fi
echo "PHASE46_SHADOW_JOURNAL_SCHEMA_INTEGRATED_REPO_HYGIENE_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "Shadow decision allowed: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
echo "Repo hygiene: PASS"
