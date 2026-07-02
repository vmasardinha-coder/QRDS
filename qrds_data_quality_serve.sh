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
bash qrds_data_quality.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
SERVE_DIR="$(pwd)/crypto_decision_lab/$OUTPUT_DIR"
PORT="${PORT:-}"
if [ -z "$PORT" ]; then
  PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()
PY
)"
fi
echo ""
echo "[QRDS 9C] Data Quality site ready."
echo "[QRDS 9C] Serve directory: $SERVE_DIR"
echo "[QRDS 9C] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
