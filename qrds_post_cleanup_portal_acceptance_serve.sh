#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/post_cleanup_portal_acceptance"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"

echo "[QRDS 9Y] Building Post-Cleanup Portal Acceptance..."
bash "$ROOT/qrds_post_cleanup_portal_acceptance.sh" "$OUT"

PORT="$(python - <<'PY'
import socket
for port in range(8136, 8200):
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
echo "[QRDS 9Y] Post-Cleanup Portal Acceptance ready."
echo "[QRDS 9Y] Serve directory: $OUT"
echo "[QRDS 9Y] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
