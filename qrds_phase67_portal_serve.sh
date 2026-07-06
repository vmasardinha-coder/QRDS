#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
PROJ="$ROOT/crypto_decision_lab"
cd "$PROJ"
export PYTHONPATH="$PROJ/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase67_runner_preflight_integration_research_only
OUT="$PROJ/artifacts/phase67_runner_preflight_integration_research_only"
PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()
PY
)"
echo "[QRDS][Phase67] Serving $OUT on port $PORT"
echo "[QRDS][Phase67] Use Codespaces Ports tab for port $PORT"
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
