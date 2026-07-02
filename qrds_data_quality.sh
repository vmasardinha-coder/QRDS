#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUTPUT_DIR="artifacts/data_quality"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --reports) REPORTS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
cd crypto_decision_lab
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m crypto_decision_lab.cli.data_quality --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
