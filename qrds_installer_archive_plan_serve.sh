#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/installer_archive_plan"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
mkdir -p "$OUT"
echo "[QRDS 9V] Building installer archive / repo slimdown plan..."
cd "$PROJECT"
python -m crypto_decision_lab.cli.installer_archive_plan --output-dir "$OUT" --repo-root "$ROOT"
PORT="$(python - <<'PY'
import socket
for port in range(8135, 8200):
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
echo "[QRDS 9V] Installer Archive Plan ready."
echo "[QRDS 9V] Serve directory: $OUT"
echo "[QRDS 9V] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$OUT"
python -m http.server "$PORT" --bind 0.0.0.0
