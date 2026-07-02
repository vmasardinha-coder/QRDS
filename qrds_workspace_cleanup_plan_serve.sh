#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-/workspaces/QRDS}"
cd "$ROOT"
bash qrds_workspace_cleanup_plan.sh
SERVE_DIR="$ROOT/crypto_decision_lab/artifacts/workspace_cleanup_plan"
PORT="${PORT:-8134}"
while lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
  PORT=$((PORT + 1))
done
cat <<EOF2

[QRDS 9Q] Controlled Cleanup Plan site ready.
[QRDS 9Q] Serve directory: $SERVE_DIR
[QRDS 9Q] Port: $PORT

Codespaces:
  Ports -> $PORT -> Open in Browser / Open Preview

Stop server with Ctrl+C.
EOF2
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
