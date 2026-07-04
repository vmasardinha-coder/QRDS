#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase13_hyperliquid_public_data_adapter_pack}"
COINS="${QRDS_HL_COINS:-BTC,ETH,SOL}"
INTERVAL="${QRDS_HL_INTERVAL:-1h}"
ROWS="${QRDS_HL_ROWS_PER_COIN:-5000}"
python -m crypto_decision_lab.cli.phase13_hyperliquid_public_data_adapter_pack --output-dir "$OUT" --repo-root "$ROOT" --coins "$COINS" --interval "$INTERVAL" --rows-per-coin "$ROWS"
