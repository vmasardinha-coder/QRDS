#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 30A-30R] Building No-Edge Checkpoint + Dashboard Readiness Pack..."
bash "$ROOT/qrds_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8172, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind(("0.0.0.0", port))
        except OSError: continue
        print(port); break
else: raise SystemExit("NO_FREE_PORT")
PY
)"
echo
echo "[QRDS 30A-30R] No-Edge Checkpoint + Dashboard Readiness Pack ready."
echo "[QRDS 30A-30R] Serve directory: $OUT"
echo "[QRDS 30A-30R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
cd "$OUT"; python -m http.server "$PORT" --bind 0.0.0.0
