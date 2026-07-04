#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase14_okx_public_data_adapter_pack}"
INST_IDS="${QRDS_OKX_INST_IDS:-BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP}"
BAR="${QRDS_OKX_BAR:-1H}"
ROWS="${QRDS_OKX_ROWS_PER_INSTRUMENT:-5000}"
python -m crypto_decision_lab.cli.phase14_okx_public_data_adapter_pack --output-dir "$OUT" --repo-root "$ROOT" --inst-ids "$INST_IDS" --bar "$BAR" --rows-per-instrument "$ROWS"
