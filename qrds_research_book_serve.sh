#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/research_book"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    *)
      echo "[QRDS 8W] Unknown argument: $1" >&2; exit 2 ;;
  esac
done

cd "$ROOT_DIR"
bash qrds_research_book.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS"

SERVE_DIR="$ROOT_DIR/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8W] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi

PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8133, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("No free port found in 8133-8198")
PY
)"
fi

echo
echo "[QRDS 8W] Research Book site ready."
echo "[QRDS 8W] Serve directory: $SERVE_DIR"
echo "[QRDS 8W] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
