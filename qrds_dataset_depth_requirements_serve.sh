#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/dataset_depth_requirements"
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [ "${ARGS[$i]}" = "--output-dir" ] && [ $((i+1)) -lt ${#ARGS[@]} ]; then
    OUTPUT_DIR="${ARGS[$((i+1))]}"
  fi
done
cd "$ROOT"
bash qrds_dataset_depth_requirements.sh "$@"
SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [ ! -f "$SERVE_DIR/index.html" ]; then
  echo "[QRDS 9M] ERROR: index.html not found at $SERVE_DIR" >&2
  exit 1
fi
PORT="$(python - <<'PY'
import socket
for port in range(8132, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            print(port)
            raise SystemExit
        except OSError:
            pass
raise SystemExit("no free port")
PY
)"
echo
echo "[QRDS 9M] Dataset Depth Requirements site ready."
echo "[QRDS 9M] Serve directory: $SERVE_DIR"
echo "[QRDS 9M] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python3 -m http.server "$PORT" --bind 0.0.0.0
