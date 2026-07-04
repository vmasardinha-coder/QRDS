#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase25_volatility_feature_baseline_strengthening_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 25A-25R] Building Volatility Feature + Baseline Strengthening Pack..."
bash "$ROOT/qrds_phase25_volatility_feature_baseline_strengthening_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8167, 8200):
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
echo "[QRDS 25A-25R] Volatility Feature + Baseline Strengthening Pack ready."
echo "[QRDS 25A-25R] Serve directory: $OUT"
echo "[QRDS 25A-25R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
