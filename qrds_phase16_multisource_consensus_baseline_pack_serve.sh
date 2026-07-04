#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase16_multisource_consensus_baseline_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 16A-16R] Building Multi-source Consensus Baseline Pack..."
bash "$ROOT/qrds_phase16_multisource_consensus_baseline_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8158, 8200):
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
echo "[QRDS 16A-16R] Multi-source Consensus Baseline Pack ready."
echo "[QRDS 16A-16R] Serve directory: $OUT"
echo "[QRDS 16A-16R] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
