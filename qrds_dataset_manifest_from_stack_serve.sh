#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
OUTPUT_DIR="artifacts/dataset_manifest"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9E] Refreshing evidence stack before Dataset Manifest Pack..."
if [[ -x "./qrds_evidence_stack.sh" ]]; then
  bash ./qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/tmp/qrds_9e_stack.log 2>&1 || cat /tmp/qrds_9e_stack.log
fi

REPORTS=()
CANDIDATES=(
  "crypto_decision_lab/artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/evidence_drilldown/evidence_drilldown_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/evidence_timeline/evidence_timeline_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/research_promotion/research_promotion_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/human_review/human_review_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/oos_validation/oos_validation_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/paper_trading/paper_trading_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/risk_model/risk_model_gate.json"
  "crypto_decision_lab/artifacts/operational_security/operational_security_gate.json"
  "crypto_decision_lab/artifacts/data_coverage/data_coverage_gate.json"
  "crypto_decision_lab/artifacts/data_quality/data_quality_gate.json"
  "crypto_decision_lab/artifacts/data_audit/data_audit_evidence_pack.json"
)
for p in "${CANDIDATES[@]}"; do
  if [[ -f "$p" ]]; then
    REPORTS+=("$p")
  fi
done
REPORTS_CSV="$(IFS=,; echo "${REPORTS[*]:-}")"
echo "[QRDS 9E] Explicit reports found: ${REPORTS_CSV:-NONE}"

ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS")
if [[ -n "$REPORTS_CSV" ]]; then
  ARGS+=(--reports "$REPORTS_CSV")
fi
bash qrds_dataset_manifest_serve.sh "${ARGS[@]}"
