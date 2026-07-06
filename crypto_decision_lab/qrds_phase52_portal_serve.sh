#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase52_manual_shadow_journal_workflow_research_only
OUT_DIR="$PROJECT_DIR/artifacts/phase52_manual_shadow_journal_workflow_research_only"
PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()
PY
)"
echo "[QRDS][Phase52] Serving $OUT_DIR on port $PORT"
echo "[QRDS][Phase52] Use Codespaces Ports tab for port $PORT"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
