#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase18_research_feature_regime_diagnostics_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 18A-18R] Building Research Feature + Regime Diagnostics Pack..."
bash "$ROOT/qrds_phase18_research_feature_regime_diagnostics_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8160, 8200):
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
echo "[QRDS 18A-18R] Research Feature + Regime Diagnostics Pack ready."
echo "[QRDS 18A-18R] Serve directory: $OUT"
echo "[QRDS 18A-18R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
