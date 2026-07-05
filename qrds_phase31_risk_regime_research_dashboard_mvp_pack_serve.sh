#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase31_risk_regime_research_dashboard_mvp_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 31A-31R] Building Risk/Regime Research Dashboard MVP Pack..."
bash "$ROOT/qrds_phase31_risk_regime_research_dashboard_mvp_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8173, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("NO_FREE_PORT")
PY
)"
python - "$OUT" "$PORT" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
out = Path(sys.argv[1])
port = int(sys.argv[2])
plan = {
    "schema": "qrds.phase31_dashboard_serve_plan.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "serve_directory": str(out),
    "port": port,
    "url": f"http://127.0.0.1:{port}/",
    "codespaces_instruction": f"Ports -> {port} -> Open in Browser / Open Preview",
    "entrypoint": "index.html",
    "research_only": True,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}
(out / "dashboard_serve_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
PY
echo
echo "[QRDS 31A-31R] Risk/Regime Research Dashboard MVP ready."
echo "[QRDS 31A-31R] Serve directory: $OUT"
echo "[QRDS 31A-31R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
