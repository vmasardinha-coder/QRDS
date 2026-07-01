#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_JSON="$(mktemp)"
cleanup() { rm -f "$TMP_JSON"; }
trap cleanup EXIT

"$ROOT_DIR/qrds_oos_validation.sh" "$@" | tee "$TMP_JSON"

SERVE_ENTRYPOINT="$(python - "$TMP_JSON" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding='utf-8'))
print(payload.get('serve_entrypoint') or payload.get('html_path') or 'artifacts/oos_validation/index.html')
PY
)"

SERVE_DIR="$(python - "$ROOT_DIR" "$SERVE_ENTRYPOINT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
entry = Path(sys.argv[2])
if entry.is_absolute():
    target = entry
else:
    target = root / 'crypto_decision_lab' / entry
target = target.resolve()
print(target.parent)
PY
)"

PORT="$(python - <<'PY'
import socket
for port in range(8133, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit('No free port found in 8133-8198')
PY
)"

echo ""
echo "[QRDS 8Q] OOS Validation Gate site ready."
echo "[QRDS 8Q] Serve directory: $SERVE_DIR"
echo "[QRDS 8Q] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
