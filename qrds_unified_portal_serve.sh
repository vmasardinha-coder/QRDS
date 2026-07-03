#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
if [ ! -d "$ROOT/crypto_decision_lab" ]; then
  ROOT="$(pwd)"
fi
cd "$ROOT/crypto_decision_lab"
python -m crypto_decision_lab.cli.portal_unification_suite --output-dir artifacts/unified_portal_suite --repo-root "$ROOT"
cd "$ROOT"
PORT="${QRDS_PORT:-}"
if [ -z "$PORT" ]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8134, 8199):
    s = socket.socket()
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        print(port)
        break
    except OSError:
        s.close()
PY
)
fi
ENTRY="/crypto_decision_lab/artifacts/unified_portal_suite/index.html"
echo "[QRDS 9U] Unified Portal Launcher ready."
echo "[QRDS 9U] Serve root: $ROOT"
echo "[QRDS 9U] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Open path: $ENTRY"
echo "Full URL after opening port: http://localhost:$PORT$ENTRY"
echo
echo "Stop server with Ctrl+C."
python -m http.server "$PORT" --bind 0.0.0.0
