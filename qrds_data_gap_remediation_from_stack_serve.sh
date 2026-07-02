#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
OUTPUT_DIR="artifacts/data_gap_remediation"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9I] Refreshing evidence/data stack before Data Gap Remediation Plan..."
if [[ -x "qrds_evidence_stack.sh" ]]; then
  bash qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/dev/null || true
fi

reports=(
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
  "crypto_decision_lab/artifacts/dataset_manifest/dataset_manifest_pack.json"
  "crypto_decision_lab/artifacts/data_profile/data_profile_pack.json"
  "crypto_decision_lab/artifacts/data_readiness/data_readiness_matrix.json"
)
existing=()
for r in "${reports[@]}"; do
  [[ -f "$r" ]] && existing+=("$r")
done
REPORTS=$(IFS=,; echo "${existing[*]}")
echo "[QRDS 9I] Explicit reports found: $REPORTS"
exec bash qrds_data_gap_remediation_serve.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
