#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase14_bybit_public_data_adapter_pack}"
SYMBOLS="${QRDS_BYBIT_SYMBOLS:-BTCUSDT,ETHUSDT,SOLUSDT}"
CATEGORY="${QRDS_BYBIT_CATEGORY:-linear}"
INTERVAL="${QRDS_BYBIT_INTERVAL:-60}"
ROWS="${QRDS_BYBIT_ROWS_PER_SYMBOL:-5000}"
python -m crypto_decision_lab.cli.phase14_bybit_public_data_adapter_pack --output-dir "$OUT" --repo-root "$ROOT" --symbols "$SYMBOLS" --category "$CATEGORY" --interval "$INTERVAL" --rows-per-symbol "$ROWS"
