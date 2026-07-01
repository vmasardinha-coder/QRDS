#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/research_book_chronicle"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    *)
      EXTRA_ARGS+=("$1"); shift ;;
  esac
done
cd "$ROOT_DIR"
bash qrds_research_book_chronicle.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" "${EXTRA_ARGS[@]}"
SERVE_DIR="$ROOT_DIR/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8X] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PORTPY'
import socket
for port in range(8138, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
PORTPY
)"
fi
if [[ -z "$PORT" ]]; then
  echo "[QRDS 8X] ERROR: no free port found." >&2
  exit 1
fi
cat <<MSG

[QRDS 8X] Research Book Chronicle site ready.
[QRDS 8X] Serve directory: $SERVE_DIR
[QRDS 8X] Port: $PORT

Codespaces:
  Ports -> $PORT -> Open in Browser / Open Preview

Stop server with Ctrl+C.
MSG
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
