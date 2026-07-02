#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/data_profile"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
PORT=""
REPORTS=""
MANIFESTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --reports) REPORTS="$2"; shift 2 ;;
    --manifest-reports) MANIFESTS="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
"$ROOT/qrds_data_profile.sh" --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS" --manifest-reports "$MANIFESTS"
PROJECT="$ROOT/crypto_decision_lab"
SERVE_DIR="$PROJECT/$OUTPUT_DIR"
if [[ -z "$PORT" ]]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8138, 8189):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
            print(port)
            break
        except OSError:
            pass
PY
)
fi
echo "[QRDS 9G] Data Profile Pack site ready."
echo "[QRDS 9G] Port: $PORT"
echo "Codespaces: Ports -> $PORT -> Open in Browser / Open Preview"
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
