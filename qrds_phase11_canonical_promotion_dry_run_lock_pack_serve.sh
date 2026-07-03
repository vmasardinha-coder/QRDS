#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/phase11_canonical_promotion_dry_run_lock_pack"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 11A-11H] Building Phase 11 Canonical Promotion Dry-Run Lock Pack..."
bash "$ROOT/qrds_phase11_canonical_promotion_dry_run_lock_pack.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8146, 8200):
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
echo "[QRDS 11A-11H] Phase 11 Canonical Promotion Dry-Run Lock Pack ready."
echo "[QRDS 11A-11H] Serve directory: $OUT"
echo "[QRDS 11A-11H] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
