#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase10_offline_intake_validation_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"

echo "[QRDS 10D-10H] Building Phase 10 Offline Intake Validation Pack..."
bash "$ROOT/qrds_phase10_offline_intake_validation_pack.sh" "$OUT"

PORT="$(python - <<'PY'
import socket
for port in range(8142, 8200):
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
echo "[QRDS 10D-10H] Phase 10 Offline Intake Validation Pack ready."
echo "[QRDS 10D-10H] Serve directory: $OUT"
echo "[QRDS 10D-10H] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
