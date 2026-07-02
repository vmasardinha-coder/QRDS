#!/usr/bin/env bash
set -euo pipefail
cd /workspaces/QRDS
DIR="crypto_decision_lab/artifacts/workspace_cleanup_safe_apply"
if [ ! -f "$DIR/index.html" ]; then
  echo "Missing $DIR/index.html. Run qrds_sprint_9S_controlled_cleanup_safe_apply.sh first."
  exit 1
fi
PORT="${PORT:-}"
if [ -z "$PORT" ]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8134, 8175):
    s=socket.socket()
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
echo "[QRDS 9S] Workspace Cleanup Safe Apply site ready."
echo "[QRDS 9S] Serve directory: /workspaces/QRDS/$DIR"
echo "[QRDS 9S] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$DIR"
python -m http.server "$PORT" --bind 0.0.0.0
