#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/data_gap_remediation"
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
cd "$ROOT"
if [[ -n "$REPORTS" ]]; then
  bash qrds_data_gap_remediation.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
else
  bash qrds_data_gap_remediation.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS"
fi
SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8138, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) != 0:
            print(port)
            break
PY
)
fi
echo ""
echo "[QRDS 9I] Data Gap Remediation Plan site ready."
echo "[QRDS 9I] Serve directory: $SERVE_DIR"
echo "[QRDS 9I] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
