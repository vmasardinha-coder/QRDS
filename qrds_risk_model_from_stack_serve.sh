#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS=(
  "crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json"
  "crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json"
  "crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json"
  "crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json"
  "crypto_decision_lab/artifacts/human_review/human_review_gate.json"
  "crypto_decision_lab/artifacts/oos_validation/oos_validation_gate.json"
  "crypto_decision_lab/artifacts/paper_trading/paper_trading_gate.json"
)
EXISTING=()
for report in "${REPORTS[@]}"; do
  if [[ -f "$ROOT_DIR/$report" ]]; then
    EXISTING+=("$report")
  fi
done
REPORTS_CSV="$(IFS=,; echo "${EXISTING[*]}")"

exec bash "$ROOT_DIR/qrds_risk_model_serve.sh" \
  --output-dir artifacts/risk_model \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT \
  --reports "$REPORTS_CSV" \
  --max-portfolio-drawdown-pct 20 \
  --max-symbol-exposure-pct 35 \
  --daily-loss-limit-pct 5 \
  --stress-loss-limit-pct 30 \
  --kill-switch-present \
  --liquidity-check-present \
  --cost-model-present \
  --risk-artifact-present \
  --risk-state UNDER_REVIEW
