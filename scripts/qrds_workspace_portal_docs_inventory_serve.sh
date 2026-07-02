#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
if [ ! -d "$ROOT/crypto_decision_lab" ]; then ROOT="$(pwd)"; fi
cd "$ROOT"

echo "[QRDS 9P] Building Workspace / Portal / Docs Inventory Map..."
bash qrds_workspace_portal_docs_inventory.sh

SERVE_DIR="$ROOT/crypto_decision_lab/artifacts/workspace_portal_docs_inventory"
PORT="${PORT:-8134}"
while python - "$PORT" <<'PYPORT'
import socket, sys
port=int(sys.argv[1])
s=socket.socket()
try:
    s.bind(("0.0.0.0", port))
except OSError:
    raise SystemExit(0)
finally:
    try: s.close()
    except Exception: pass
raise SystemExit(1)
PYPORT
do
  PORT=$((PORT+1))
done

echo "[QRDS 9P] Inventory site ready."
echo "[QRDS 9P] Serve directory: $SERVE_DIR"
echo "[QRDS 9P] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
