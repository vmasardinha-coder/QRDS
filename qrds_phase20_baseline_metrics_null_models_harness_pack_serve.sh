#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase20_baseline_metrics_null_models_harness_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 20A-20R] Building Baseline Metrics + Null Models Harness Pack..."
bash "$ROOT/qrds_phase20_baseline_metrics_null_models_harness_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8162, 8200):
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
echo
echo "[QRDS 20A-20R] Baseline Metrics + Null Models Harness Pack ready."
echo "[QRDS 20A-20R] Serve directory: $OUT"
echo "[QRDS 20A-20R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
