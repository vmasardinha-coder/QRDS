#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase51_validation_automation_harness
OUT_DIR="$PROJECT_DIR/docs/reports/validation_automation"
PORT="$(python - <<'PY'
import socket
s=socket.socket(); s.bind(("",0)); print(s.getsockname()[1]); s.close()
PY
)"
cat > "$OUT_DIR/index.html" <<HTML
<!doctype html><html><head><meta charset="utf-8"><title>QRDS Phase 51 Validation Automation</title></head>
<body style="font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px">
<h1>QRDS Phase 51 • Validation Automation Harness</h1>
<p>PHASE51_VALIDATION_AUTOMATION_HARNESS_READY_RESEARCH_ONLY</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>canonical_data_writes: 0</p>
</body></html>
HTML
echo "[QRDS][Phase51] Serving $OUT_DIR on port $PORT"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
