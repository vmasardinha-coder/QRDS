#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
OUT_DIR="artifacts/operational_security"
ARGS=("$@")

for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ "${ARGS[$i]}" == "--output-dir" && $((i+1)) -lt ${#ARGS[@]} ]]; then
    OUT_DIR="${ARGS[$((i+1))]}"
  fi
done

bash "$ROOT_DIR/qrds_operational_security.sh" "$@"

if [[ "$OUT_DIR" = /* ]]; then
  SERVE_DIR="$OUT_DIR"
else
  SERVE_DIR="$PROJECT_DIR/$OUT_DIR"
fi

if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8V] ERROR: expected $SERVE_DIR/index.html" >&2
  exit 1
fi

pick_port() {
  python - <<'PY'
import socket
for port in range(8134, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)
raise SystemExit("No free port found in 8134-8198")
PY
}

PORT="${QRDS_PORT:-$(pick_port)}"

echo
echo "[QRDS 8V] Operational Security Review Gate site ready."
echo "[QRDS 8V] Serve directory: $SERVE_DIR"
echo "[QRDS 8V] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
