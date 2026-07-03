#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/canonical_data_collection_dry_run"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"

echo "[QRDS 10A] Building Canonical Data Collection Dry Run..."
bash "$ROOT/qrds_canonical_data_collection_dry_run.sh" "$OUT"

PORT="$(python - <<'PY'
import socket
for port in range(8138, 8200):
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
echo "[QRDS 10A] Canonical Data Collection Dry Run ready."
echo "[QRDS 10A] Serve directory: $OUT"
echo "[QRDS 10A] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
