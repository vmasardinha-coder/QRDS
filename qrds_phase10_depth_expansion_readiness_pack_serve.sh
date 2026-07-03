#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase10_depth_expansion_readiness_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"

echo "[QRDS 10U-10Z] Building Phase 10 Depth Expansion Readiness Pack..."
bash "$ROOT/qrds_phase10_depth_expansion_readiness_pack.sh" "$OUT"

PORT="$(python - <<'PY'
import socket
for port in range(8145, 8200):
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
echo "[QRDS 10U-10Z] Phase 10 Depth Expansion Readiness Pack ready."
echo "[QRDS 10U-10Z] Serve directory: $OUT"
echo "[QRDS 10U-10Z] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
