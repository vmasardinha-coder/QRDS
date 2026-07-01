#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OUTPUT="$(bash "$ROOT_DIR/qrds_paper_trading.sh" "$@")"
echo "$OUTPUT"

SERVE_ENTRYPOINT="$(python - <<'PY' <<<"$OUTPUT"
import json
import sys
text = sys.stdin.read()
start = text.find('{')
if start < 0:
    raise SystemExit('Could not find JSON index in CLI output')
decoder = json.JSONDecoder()
payload, _ = decoder.raw_decode(text[start:])
print(payload.get('serve_entrypoint') or payload.get('html_path'))
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
for port in range(8134, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit('No free port found in 8134-8198')
PY
)"

echo ""
echo "[QRDS 8R] Paper Trading Gate site ready."
echo "[QRDS 8R] Serve directory: $SERVE_DIR"
echo "[QRDS 8R] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
