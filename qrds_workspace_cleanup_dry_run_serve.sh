#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
OUT="crypto_decision_lab/artifacts/workspace_cleanup_dry_run"

bash "$ROOT/qrds_workspace_cleanup_dry_run.sh" "$OUT"

PORT="${PORT:-8134}"
while lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
  PORT=$((PORT + 1))
done

echo "[QRDS 9R] Workspace Cleanup Dry-Run site ready."
echo "[QRDS 9R] Serve directory: $ROOT/$OUT"
echo "[QRDS 9R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
