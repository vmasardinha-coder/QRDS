#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/dataset_evidence_explorer"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
SCAN_REPORT=""
MAX_FILES="150"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --scan-report) SCAN_REPORT="$2"; shift 2 ;;
    --max-files) MAX_FILES="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --repo-root "$ROOT" --max-files "$MAX_FILES")
if [[ -n "$SCAN_REPORT" ]]; then ARGS+=(--scan-report "$SCAN_REPORT"); fi
python -m crypto_decision_lab.cli.dataset_evidence_explorer "${ARGS[@]}"
echo "[QRDS 9L] Dataset Evidence Explorer generated: $OUTPUT_DIR/index.html"
echo "[QRDS 9L] Scope: research-only dataset drilldown; no signal, no recommendation, no order."
