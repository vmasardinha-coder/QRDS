#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
OUTPUT_DIR="artifacts/operational_security"
REFRESH_STACK=1

usage() {
  cat <<'USAGE'
QRDS Operational Security from Stack Serve v1

Refreshes 8L -> 8R, generates 8U risk model, then generates and serves the
8V operational-security review gate.

Usage:
  bash qrds_operational_security_from_stack_serve.sh \
    --output-dir artifacts/operational_security \
    --symbols BTC-USDT,ETH-USDT,SOL-USDT

Options:
  --output-dir DIR     Operational-security output directory.
  --symbols LIST       Comma-separated symbols.
  --skip-refresh       Do not rerun 8S/8U; use existing artifacts if present.
  -h, --help           Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:?missing value for --output-dir}"; shift 2 ;;
    --output-dir=*) OUTPUT_DIR="${1#--output-dir=}"; shift ;;
    --symbols) SYMBOLS="${2:?missing value for --symbols}"; shift 2 ;;
    --symbols=*) SYMBOLS="${1#--symbols=}"; shift ;;
    --skip-refresh) REFRESH_STACK=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[QRDS 8V] ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

STACK_OUT="artifacts/evidence_stack"
STACK_ROOT="$ROOT_DIR/crypto_decision_lab/$STACK_OUT"

if [[ "$REFRESH_STACK" == "1" ]]; then
  if [[ -x "$ROOT_DIR/qrds_evidence_stack.sh" ]]; then
    echo "[QRDS 8V] Refreshing evidence stack 8L -> 8R..."
    bash "$ROOT_DIR/qrds_evidence_stack.sh" --output-dir "$STACK_OUT" --symbols "$SYMBOLS"
  else
    echo "[QRDS 8V] WARN: qrds_evidence_stack.sh not found. Will use existing reports only." >&2
  fi
fi

EVIDENCE_REPORTS=(
  "crypto_decision_lab/$STACK_OUT/evidence_quality/evidence_quality_gate.json"
  "crypto_decision_lab/$STACK_OUT/evidence_drilldown/evidence_drilldown_gate.json"
  "crypto_decision_lab/$STACK_OUT/evidence_timeline/evidence_timeline_gate.json"
  "crypto_decision_lab/$STACK_OUT/research_promotion/research_promotion_gate.json"
  "crypto_decision_lab/$STACK_OUT/human_review/human_review_gate.json"
  "crypto_decision_lab/$STACK_OUT/oos_validation/oos_validation_gate.json"
  "crypto_decision_lab/$STACK_OUT/paper_trading/paper_trading_gate.json"
)

EXISTING_EVIDENCE=()
for report in "${EVIDENCE_REPORTS[@]}"; do
  if [[ -f "$ROOT_DIR/$report" ]]; then EXISTING_EVIDENCE+=("$report"); fi
done
EVIDENCE_CSV="$(IFS=,; echo "${EXISTING_EVIDENCE[*]}")"

if [[ "$REFRESH_STACK" == "1" ]]; then
  if [[ -x "$ROOT_DIR/qrds_risk_model.sh" ]]; then
    echo "[QRDS 8V] Generating 8U risk model from refreshed stack..."
    bash "$ROOT_DIR/qrds_risk_model.sh" \
      --output-dir "$STACK_OUT/risk_model" \
      --symbols "$SYMBOLS" \
      --reports "$EVIDENCE_CSV" \
      --max-portfolio-drawdown-pct 20 \
      --max-symbol-exposure-pct 35 \
      --daily-loss-limit-pct 5 \
      --stress-loss-limit-pct 30 \
      --kill-switch-present \
      --liquidity-check-present \
      --cost-model-present \
      --risk-artifact-present \
      --risk-state UNDER_REVIEW
  else
    echo "[QRDS 8V] WARN: qrds_risk_model.sh not found. Sprint 8U must be installed for a full 8V packet." >&2
  fi
fi

REPORT_CANDIDATES=(
  "${EVIDENCE_REPORTS[@]}"
  "crypto_decision_lab/$STACK_OUT/risk_model/risk_model_gate.json"
  "crypto_decision_lab/artifacts/risk_model/risk_model_gate.json"
)

EXISTING=()
for report in "${REPORT_CANDIDATES[@]}"; do
  if [[ -f "$ROOT_DIR/$report" ]]; then EXISTING+=("$report"); fi
done
REPORTS_CSV="$(IFS=,; echo "${EXISTING[*]}")"

exec bash "$ROOT_DIR/qrds_operational_security_serve.sh" \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS_CSV" \
  --binance-mode SIMULATION_FIXTURE_REPLAY \
  --okx-mode PUBLIC_CACHE_OFFLINE \
  --bybit-mode BLOCKED_PENDING \
  --secrets-scan-state PASS \
  --security-state UNDER_REVIEW \
  --policy-lock ACTIVE
