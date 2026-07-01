#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/research_book_legacy_intake"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
BOOK_DIR="docs/book"
IMPORTS_DIR=""
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --book-dir) BOOK_DIR="$2"; shift 2 ;;
    --imports-dir) IMPORTS_DIR="$2"; shift 2 ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done
cd "$ROOT_DIR"
CMD=(bash qrds_research_book_legacy_intake.sh --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --book-dir "$BOOK_DIR")
if [[ -n "$IMPORTS_DIR" ]]; then
  CMD+=(--imports-dir "$IMPORTS_DIR")
fi
"${CMD[@]}" "${EXTRA_ARGS[@]}"
SERVE_DIR="$ROOT_DIR/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8Y] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PORTPY'
import socket
for port in range(8139, 8199):
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
  echo "[QRDS 8Y] ERROR: no free port found." >&2
  exit 1
fi
cat <<MSG

[QRDS 8Y] Research Book Legacy Intake site ready.
[QRDS 8Y] Serve directory: $SERVE_DIR
[QRDS 8Y] Port: $PORT

Codespaces:
  Ports -> $PORT -> Open in Browser / Open Preview

Stop server with Ctrl+C.
MSG
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
