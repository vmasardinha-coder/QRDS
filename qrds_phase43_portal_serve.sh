#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
BIND="${BIND:-0.0.0.0}"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase43_candidate_lifecycle_registry
OUT_DIR="$PROJECT_DIR/artifacts/phase43_candidate_lifecycle_registry"
PORT="$(python - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
)"
python - <<PY
import json
from pathlib import Path
out = Path("$OUT_DIR")
(out / "dashboard_serve_plan.json").write_text(json.dumps({"host":"$BIND","port":int("$PORT"),"output_dir":str(out),"index":"index.html"}, indent=2), encoding="utf-8")
PY
echo "[QRDS][Phase43] Open Codespaces Ports tab and make port ${PORT} public/visible if needed."
echo "[QRDS][Phase43] Serving: $OUT_DIR"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind "$BIND"
