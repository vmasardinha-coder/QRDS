#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
OUTPUT_DIR="artifacts/dataset_manifest"
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

ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS")
if [[ -n "$REPORTS" ]]; then
  ARGS+=(--reports "$REPORTS")
fi
bash qrds_dataset_manifest.sh "${ARGS[@]}"

SERVE_DIR="$REPO_ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 9E] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()
PY
)"
fi

echo ""
echo "[QRDS 9E] Dataset Manifest Pack site ready."
echo "[QRDS 9E] Serve directory: $SERVE_DIR"
echo "[QRDS 9E] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
