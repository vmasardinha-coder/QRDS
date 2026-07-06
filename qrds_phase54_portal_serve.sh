#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase54_shadow_replay_quality_bias_audit_research_only
OUT_DIR="$PROJECT_DIR/artifacts/phase54_shadow_replay_quality_bias_audit_research_only"
PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()
PY
)"
echo "[QRDS][Phase54] Serving $OUT_DIR on port $PORT"
echo "[QRDS][Phase54] Use Codespaces Ports tab for port $PORT"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
