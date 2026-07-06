#!/usr/bin/env bash
set -euo pipefail

PHASE=""
MODE="verify-only"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase)
      PHASE="${2:-}"
      shift 2
      ;;
    --verify-only)
      MODE="verify-only"
      shift
      ;;
    --run-and-verify)
      MODE="run-and-verify"
      shift
      ;;
    *)
      echo "[QRDS][Runner][ERROR] Unknown argument: $1"
      exit 2
      ;;
  esac
done

if [[ -z "$PHASE" ]]; then
  echo "[QRDS][Runner][ERROR] Usage:"
  echo "  bash qrds_next_phase_runner.sh --phase 51 --verify-only"
  echo "  bash qrds_next_phase_runner.sh --phase 52 --run-and-verify"
  exit 2
fi

ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
cd "$ROOT_DIR"

VERIFY="qrds_phase${PHASE}_verify.sh"
PACK="$(ls -1 qrds_sprint_${PHASE}A_to_${PHASE}R_*_pack.sh 2>/dev/null | head -n 1 || true)"
LOG_DIR="crypto_decision_lab/docs/reports/validation_automation"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/phase${PHASE}_runner_last.log"

echo "[QRDS][Runner] Root: $ROOT_DIR"
echo "[QRDS][Runner] Phase: $PHASE"
echo "[QRDS][Runner] Mode: $MODE"

if [[ "$MODE" == "run-and-verify" ]]; then
  if [[ -z "$PACK" ]]; then
    echo "[QRDS][Runner][ERROR] Pack not found for phase $PHASE:"
    echo "  qrds_sprint_${PHASE}A_to_${PHASE}R_*_pack.sh"
    exit 2
  fi
  echo "[QRDS][Runner] Running pack: $PACK"
  chmod +x "$PACK"
  bash "$PACK" | tee "$LOG_FILE"
fi

if [[ ! -f "$VERIFY" ]]; then
  echo "[QRDS][Runner][ERROR] Verify script not found: $VERIFY"
  echo "[QRDS][Runner] If this is a new phase, run with --run-and-verify first."
  exit 2
fi

echo "[QRDS][Runner] Running verify: $VERIFY"
bash "$VERIFY" | tee -a "$LOG_FILE"

echo
echo "[QRDS][Runner] Validation complete for Phase $PHASE."
