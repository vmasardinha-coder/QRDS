#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
PROJ="$ROOT/crypto_decision_lab"
cd "$PROJ"
export PYTHONPATH="$PROJ/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase78_journal_replay_release_checkpoint_research_only
OUT="$PROJ/docs/reports/journal_replay"
PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()
PY
)"
echo "[QRDS][Phase78] Serving $OUT on port $PORT"
echo "[QRDS][Phase78] Use Codespaces Ports tab for port $PORT"
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
