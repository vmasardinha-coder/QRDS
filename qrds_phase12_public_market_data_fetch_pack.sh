#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase12_public_market_data_fetch_pack}"
SYMBOLS="${QRDS_PUBLIC_SYMBOLS:-BTCUSDT,ETHUSDT,SOLUSDT}"
INTERVAL="${QRDS_PUBLIC_INTERVAL:-1h}"
ROWS="${QRDS_PUBLIC_ROWS_PER_SYMBOL:-5000}"
python -m crypto_decision_lab.cli.phase12_public_market_data_fetch_pack --output-dir "$OUT" --repo-root "$ROOT" --symbols "$SYMBOLS" --interval "$INTERVAL" --rows-per-symbol "$ROWS"
