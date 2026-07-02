#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/data_audit"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=""
DATASET_MANIFESTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --reports) REPORTS="$2"; shift 2 ;;
    --dataset-manifests) DATASET_MANIFESTS="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
cd "$REPO_ROOT"
ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS")
if [[ -n "$REPORTS" ]]; then ARGS+=(--reports "$REPORTS"); fi
if [[ -n "$DATASET_MANIFESTS" ]]; then ARGS+=(--dataset-manifests "$DATASET_MANIFESTS"); fi
bash qrds_data_audit.sh "${ARGS[@]}"
SERVE_DIR="$REPO_ROOT/crypto_decision_lab/$OUTPUT_DIR"
PORT="$(python - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)"
echo
echo "[QRDS 9D] Data Audit Evidence Pack site ready."
echo "[QRDS 9D] Serve directory: $SERVE_DIR"
echo "[QRDS 9D] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
