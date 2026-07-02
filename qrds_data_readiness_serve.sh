#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/data_readiness"
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
if [[ " ${ARGS[*]} " != *" --output-dir "* ]]; then
  ARGS=(--output-dir "$OUTPUT_DIR" "${ARGS[@]}")
fi
cd "$ROOT"
bash qrds_data_readiness.sh "${ARGS[@]}"
SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [[ "$OUTPUT_DIR" = /* ]]; then
  SERVE_DIR="$OUTPUT_DIR"
fi
PORT="$(python - <<'PY'
import socket
for port in range(8132, 8199):
    with socket.socket() as s:
        try:
            s.bind(("", port))
            print(port)
            raise SystemExit
        except OSError:
            pass
print(8199)
PY
)"
echo ""
echo "[QRDS 9H] Data Readiness Matrix site ready."
echo "[QRDS 9H] Serve directory: $SERVE_DIR"
echo "[QRDS 9H] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
