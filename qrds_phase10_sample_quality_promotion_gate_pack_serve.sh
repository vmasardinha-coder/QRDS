#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase10_sample_quality_promotion_gate_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"

echo "[QRDS 10O-10T] Building Phase 10 Sample Quality / Promotion Gate Pack..."
bash "$ROOT/qrds_phase10_sample_quality_promotion_gate_pack.sh" "$OUT"

PORT="$(python - <<'PY'
import socket
for port in range(8144, 8200):
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
echo "[QRDS 10O-10T] Phase 10 Sample Quality / Promotion Gate Pack ready."
echo "[QRDS 10O-10T] Serve directory: $OUT"
echo "[QRDS 10O-10T] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
