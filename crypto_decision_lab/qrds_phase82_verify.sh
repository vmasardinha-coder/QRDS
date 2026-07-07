#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
PROJ="$ROOT/crypto_decision_lab"
cd "$PROJ"
export PYTHONPATH="$PROJ/src:${PYTHONPATH:-}"
echo "[QRDS][Phase82] Running focused tests..."
python -m pytest tests/unit/test_phase82_journal_replay_batch_intake_checkpoint_research_only.py -q
echo "[QRDS][Phase82] Running local preflight smoke..."
bash "$ROOT/qrds_local_preflight.sh" >/tmp/qrds_phase82_preflight.out
echo "[QRDS][Phase82] Running full suite..."
python -m pytest -q
echo "PHASE82_JOURNAL_REPLAY_BATCH_INTAKE_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "Shadow decision allowed: False"
echo "Decision layer allowed: False"
echo "Promotion allowed: False"
echo "safe_apply_allowed: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
