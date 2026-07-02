#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/data_coverage"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=""
ARGS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; ARGS+=("$1" "$2"); shift 2 ;;
    --symbols) SYMBOLS="$2"; ARGS+=("$1" "$2"); shift 2 ;;
    --reports) REPORTS="$2"; ARGS+=("$1" "$2"); shift 2 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
cd "$ROOT"
bash qrds_data_coverage.sh "${ARGS[@]}"
SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [ ! -f "$SERVE_DIR/index.html" ]; then
  echo "[QRDS 9B] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="${QRDS_PORT:-}"
if [ -z "$PORT" ]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8132, 8199):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
PY
)"
fi
cat <<MSG

[QRDS 9B] Data Coverage Gate site ready.
[QRDS 9B] Serve directory: $SERVE_DIR
[QRDS 9B] Port: $PORT

Codespaces:
  Ports -> $PORT -> Open in Browser / Open Preview

Stop server with Ctrl+C.
MSG
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
