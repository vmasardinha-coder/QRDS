#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
OUT="crypto_decision_lab/artifacts/data_source_contract"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=()
for f in \
  crypto_decision_lab/artifacts/data_acquisition_depth_plan/data_acquisition_depth_plan_index.json \
  crypto_decision_lab/artifacts/dataset_depth_requirements/dataset_depth_requirements_index.json \
  crypto_decision_lab/artifacts/dataset_evidence_explorer/dataset_evidence_explorer_index.json \
  crypto_decision_lab/artifacts/dataset_evidence_scan/dataset_evidence_scan_index.json \
  crypto_decision_lab/artifacts/data_readiness/data_readiness_matrix.json \
  crypto_decision_lab/artifacts/data_gap_remediation/data_gap_remediation_plan.json; do
  if [ -f "$f" ]; then REPORTS+=("$PWD/$f"); fi
done
REPORTS_CSV="$(IFS=,; echo "${REPORTS[*]:-}")"
cd crypto_decision_lab
python -m crypto_decision_lab.cli.data_source_contract \
  --output-dir artifacts/data_source_contract \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS_CSV"
