#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
BIND="${BIND:-0.0.0.0}"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase48_portfolio_context_schema_research_only
OUT_DIR="$PROJECT_DIR/artifacts/phase48_portfolio_context_schema_research_only"
python - <<'PY'
import json, socket
from pathlib import Path
out = Path("artifacts/phase48_portfolio_context_schema_research_only")
s = socket.socket(); s.bind(("", 0)); port = s.getsockname()[1]; s.close()
plan = {"host":"0.0.0.0","port":port,"output_dir":str(out),"index":"index.html"}
(out/"dashboard_serve_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
print(port)
PY
PORT="$(python - <<'PY'
import json
from pathlib import Path
print(json.loads((Path("artifacts/phase48_portfolio_context_schema_research_only")/"dashboard_serve_plan.json").read_text())["port"])
PY
)"
echo "[QRDS][Phase48] Open Codespaces Ports tab and make port ${PORT} public/visible if needed."
echo "[QRDS][Phase48] Serving: $OUT_DIR"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind "$BIND"
