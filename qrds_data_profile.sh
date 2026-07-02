#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/data_profile"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=""
MANIFEST_REPORTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --reports) REPORTS="$2"; shift 2 ;;
    --manifest-reports) MANIFEST_REPORTS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
cd "$PROJECT"
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m crypto_decision_lab.cli.data_profile \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS" \
  --manifest-reports "$MANIFEST_REPORTS"
