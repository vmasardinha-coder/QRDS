#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="/workspaces/QRDS"
if [[ ! -d "$ROOT/crypto_decision_lab" ]]; then
  if [[ -d "$(pwd)/crypto_decision_lab" ]]; then
    ROOT="$(pwd)"
  elif [[ "$(basename "$(pwd)")" == "crypto_decision_lab" ]]; then
    ROOT="$(dirname "$(pwd)")"
  else
    echo "[QRDS][VERIFY][ERROR] Cannot locate QRDS root."
    exit 2
  fi
fi
cd "$ROOT/crypto_decision_lab"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
echo "[QRDS][VERIFY] cwd=$PWD"
echo "[QRDS][VERIFY] Running focused Phase 39 tests when available..."
python -m pytest -q tests -k "phase39 or interpretation_readiness or portal" || FOCUSED_RC=$?
FOCUSED_RC="${FOCUSED_RC:-0}"
echo "[QRDS][VERIFY] Running full suite from crypto_decision_lab..."
python -m pytest -q tests
FULL_RC=$?
echo "[QRDS][VERIFY] focused_rc=$FOCUSED_RC full_rc=$FULL_RC"
exit "$FULL_RC"
