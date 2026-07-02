#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "[QRDS 9O] Refreshing Data Source Contract from stack..."
bash qrds_data_source_contract_from_stack.sh

SERVE_DIR="$ROOT/crypto_decision_lab/artifacts/data_source_contract"
PORT="${PORT:-8134}"
while python - <<PY >/dev/null 2>&1
import socket
s=socket.socket(); s.bind(('0.0.0.0', int('$PORT'))); s.close()
PY
[ $? -ne 0 ]; do
  PORT=$((PORT+1))
done

echo
echo "[QRDS 9O] Data Source Contract site ready."
echo "[QRDS 9O] Serve directory: $SERVE_DIR"
echo "[QRDS 9O] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
