#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/canonical_data_collection_dry_run}"
python -m crypto_decision_lab.cli.canonical_data_collection_dry_run \
  --output-dir "$OUT" \
  --repo-root "$ROOT" \
  --symbols "${QRDS_SYMBOLS:-BTC-USDT,ETH-USDT,SOL-USDT}" \
  --target-rows-per-symbol "${QRDS_TARGET_ROWS_PER_SYMBOL:-5000}" \
  --interval "${QRDS_INTERVAL:-1h}"
