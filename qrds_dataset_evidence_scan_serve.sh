#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
OUTPUT_DIR="artifacts/dataset_evidence_scan"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
SCAN_ROOTS=""
MIN_ROWS="1000"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --scan-roots) SCAN_ROOTS="$2"; shift 2 ;;
    --min-rows-per-symbol) MIN_ROWS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --min-rows-per-symbol "$MIN_ROWS")
if [[ -n "$SCAN_ROOTS" ]]; then ARGS+=(--scan-roots "$SCAN_ROOTS"); fi
bash qrds_dataset_evidence_scan.sh "${ARGS[@]}"

SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 9K] index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="${PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8138, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
PY
)
fi

echo
echo "[QRDS 9K] Dataset Evidence Scanner site ready."
echo "[QRDS 9K] Serve directory: $SERVE_DIR"
echo "[QRDS 9K] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
