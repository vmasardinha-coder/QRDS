#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/evidence_timeline"
PORT="${QRDS_PORT:-}"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"
      ARGS+=("$1" "$2")
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

bash "$SCRIPT_DIR/qrds_evidence_timeline.sh" "${ARGS[@]}"

PROJECT_ROOT="$SCRIPT_DIR/crypto_decision_lab"
cd "$PROJECT_ROOT"

if [[ "$OUTPUT_DIR" = /* ]]; then
  SERVE_DIR="$OUTPUT_DIR"
else
  SERVE_DIR="$PROJECT_ROOT/$OUTPUT_DIR"
fi

if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8N] ERROR: index.html not found under $SERVE_DIR" >&2
  exit 1
fi

choose_port() {
  python - <<'PY'
import socket
for port in range(8130, 8180):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)
raise SystemExit(1)
PY
}

if [[ -z "$PORT" ]]; then
  PORT_TO_USE="$(choose_port)"
else
  PORT_TO_USE="$PORT"
fi

cat <<EOF

[QRDS 8N] Evidence Timeline site ready.
[QRDS 8N] Serve directory: $SERVE_DIR
[QRDS 8N] Port: $PORT_TO_USE

Codespaces:
  Ports -> $PORT_TO_USE -> Open in Browser / Open Preview

Stop server with Ctrl+C.
EOF

cd "$SERVE_DIR"
exec python -m http.server "$PORT_TO_USE" --bind 0.0.0.0
