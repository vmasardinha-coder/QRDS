#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_REPO_ROOT:-/workspaces/QRDS}"
OUT="${1:-artifacts/portal_reconciliation}"
cd "$ROOT/crypto_decision_lab"
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.portal_reconciliation --output-dir "$OUT" --repo-root "$ROOT"
PORT="${QRDS_PORT:-}"
if [ -z "$PORT" ]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8134, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
        except OSError:
            continue
        print(port)
        break
PY
)
fi
SERVE_DIR="$PWD/$OUT"
echo "[QRDS 9T] Portal Reconciliation site ready."
echo "[QRDS 9T] Serve directory: $SERVE_DIR"
echo "[QRDS 9T] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
