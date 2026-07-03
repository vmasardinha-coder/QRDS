#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/archive_manifest_repo_hygiene"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 9X] Building Archive Manifest / Repo Hygiene Index..."
bash "$ROOT/qrds_archive_manifest_repo_hygiene.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8135, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind(('0.0.0.0', port))
        except OSError: continue
        print(port); break
else: raise SystemExit('NO_FREE_PORT')
PY
)"
echo; echo "[QRDS 9X] Archive Manifest / Repo Hygiene Index ready."; echo "[QRDS 9X] Serve directory: $OUT"; echo "[QRDS 9X] Port: $PORT"; echo; echo "Codespaces:"; echo "  Ports -> $PORT -> Open in Browser / Open Preview"; echo; echo "Stop server with Ctrl+C."
cd "$OUT"; python -m http.server "$PORT" --bind 0.0.0.0
