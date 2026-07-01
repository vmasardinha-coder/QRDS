#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
PROJECT_ROOT="$REPO_ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/evidence_drilldown"
PREFERRED_PORT="${QRDS_PORT:-${PORT:-8129}}"

ARGS=("$@")
GEN_ARGS=()
i=0
while [[ $i -lt ${#ARGS[@]} ]]; do
  arg="${ARGS[$i]}"
  case "$arg" in
    --output-dir)
      if [[ $((i + 1)) -lt ${#ARGS[@]} ]]; then
        OUTPUT_DIR="${ARGS[$((i + 1))]}"
        GEN_ARGS+=("$arg" "${ARGS[$((i + 1))]}")
        i=$((i + 1))
      else
        GEN_ARGS+=("$arg")
      fi
      ;;
    --output-dir=*)
      OUTPUT_DIR="${arg#--output-dir=}"
      GEN_ARGS+=("$arg")
      ;;
    --port)
      if [[ $((i + 1)) -lt ${#ARGS[@]} ]]; then
        PREFERRED_PORT="${ARGS[$((i + 1))]}"
        i=$((i + 1))
      fi
      ;;
    --port=*)
      PREFERRED_PORT="${arg#--port=}"
      ;;
    *)
      GEN_ARGS+=("$arg")
      ;;
  esac
  i=$((i + 1))
done

bash "$REPO_ROOT/qrds_evidence_drilldown.sh" "${GEN_ARGS[@]}"

if [[ "$OUTPUT_DIR" = /* ]]; then
  SERVE_DIR="$OUTPUT_DIR"
else
  SERVE_DIR="$PROJECT_ROOT/$OUTPUT_DIR"
fi
SERVE_DIR="$(cd "$SERVE_DIR" && pwd)"

if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8M] ERROR: index.html not found in $SERVE_DIR" >&2
  exit 1
fi

PORT_TO_USE="$(python - "$PREFERRED_PORT" <<'PY'
import socket
import sys
preferred = int(sys.argv[1])
for port in range(preferred, preferred + 200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("0.0.0.0", 0))
    print(sock.getsockname()[1])
PY
)"

cat <<EOF

[QRDS 8M] Evidence Drilldown site ready.
[QRDS 8M] Serve directory: $SERVE_DIR
[QRDS 8M] Port: $PORT_TO_USE

Codespaces:
  Ports -> $PORT_TO_USE -> Open in Browser / Open Preview

Stop server with Ctrl+C.
EOF

cd "$SERVE_DIR"
exec python -m http.server "$PORT_TO_USE" --bind 0.0.0.0
