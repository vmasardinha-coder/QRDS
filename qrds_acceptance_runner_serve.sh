#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB="$ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/acceptance_runner"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    --skip-pytest|--skip-refresh)
      EXTRA_ARGS+=("$1"); shift ;;
    *)
      echo "[QRDS 9F] Unknown argument: $1" >&2
      exit 2 ;;
  esac
done

bash "$ROOT/qrds_acceptance_runner.sh" --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" "${EXTRA_ARGS[@]}"

SERVE_DIR="$LAB/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 9F] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi

PORT="$(python - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)"

echo
echo "[QRDS 9F] Acceptance Runner site ready."
echo "[QRDS 9F] Serve directory: $SERVE_DIR"
echo "[QRDS 9F] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."

cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
