#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
OUTPUT_DIR="artifacts/data_quality"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9C] Refreshing evidence stack and coverage before Data Quality Gate..."
if [ -x ./qrds_evidence_stack.sh ]; then
  bash ./qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/dev/null || true
fi

REPORTS=""
add_report() {
  local p="$1"
  if [ -f "$p" ]; then
    if [ -z "$REPORTS" ]; then REPORTS="$p"; else REPORTS="$REPORTS,$p"; fi
  fi
}

add_report "crypto_decision_lab/artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/evidence_drilldown/evidence_drilldown_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/evidence_timeline/evidence_timeline_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/research_promotion/research_promotion_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/human_review/human_review_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/oos_validation/oos_validation_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/paper_trading/paper_trading_gate.json"
add_report "crypto_decision_lab/artifacts/evidence_stack/risk_model/risk_model_gate.json"
add_report "crypto_decision_lab/artifacts/operational_security/operational_security_gate.json"

if [ -x ./qrds_data_coverage.sh ]; then
  bash ./qrds_data_coverage.sh --output-dir artifacts/data_coverage --symbols "$SYMBOLS" --reports "$REPORTS" >/dev/null || true
fi
add_report "crypto_decision_lab/artifacts/data_coverage/data_coverage_gate.json"

echo "[QRDS 9C] Explicit reports found: $REPORTS"
bash ./qrds_data_quality_serve.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
