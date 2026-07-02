#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
OUTPUT_DIR="artifacts/data_audit"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9D] Refreshing evidence stack before Data Audit Evidence Pack..."
if [[ -x "qrds_evidence_stack.sh" ]]; then
  bash qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/tmp/qrds_9d_stack.log 2>&1 || cat /tmp/qrds_9d_stack.log
fi

REPORT_PATHS=(
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
)
REPORTS=""
for p in "${REPORT_PATHS[@]}"; do
  if [[ -f "$p" ]]; then
    if [[ -z "$REPORTS" ]]; then REPORTS="$p"; else REPORTS="$REPORTS,$p"; fi
  fi
done

MANIFESTS=""
for p in crypto_decision_lab/artifacts/dataset_audit/*.json crypto_decision_lab/artifacts/datasets/*audit*.json crypto_decision_lab/artifacts/research_data/*manifest*.json; do
  if [[ -f "$p" ]]; then
    if [[ -z "$MANIFESTS" ]]; then MANIFESTS="$p"; else MANIFESTS="$MANIFESTS,$p"; fi
  fi
done

echo "[QRDS 9D] Explicit reports found: ${REPORTS:-NONE}"
echo "[QRDS 9D] Dataset manifests found: ${MANIFESTS:-NONE}"
ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS")
if [[ -n "$REPORTS" ]]; then ARGS+=(--reports "$REPORTS"); fi
if [[ -n "$MANIFESTS" ]]; then ARGS+=(--dataset-manifests "$MANIFESTS"); fi
bash qrds_data_audit_serve.sh "${ARGS[@]}"
