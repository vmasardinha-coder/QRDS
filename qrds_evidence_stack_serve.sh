#!/usr/bin/env bash
# QRDS_MANAGED_VENV_PYTHON_BOOTSTRAP_BEGIN
QRDS_BOOTSTRAP_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QRDS_VENV_PYTHON=""
for QRDS_PYTHON_CANDIDATE in \
  "$QRDS_BOOTSTRAP_SCRIPT_DIR/../crypto_decision_lab/.venv/Scripts/python.exe" \
  "$QRDS_BOOTSTRAP_SCRIPT_DIR/crypto_decision_lab/.venv/Scripts/python.exe"
do
  if [[ -x "$QRDS_PYTHON_CANDIDATE" ]]; then
    QRDS_VENV_PYTHON="$QRDS_PYTHON_CANDIDATE"
    break
  fi
done
if [[ -z "$QRDS_VENV_PYTHON" ]]; then
  echo "QRDS project Python was not found under crypto_decision_lab/.venv/Scripts/python.exe" >&2
  exit 49
fi
QRDS_VENV_SCRIPTS="$(dirname "$QRDS_VENV_PYTHON")"
export QRDS_VENV_PYTHON
export QRDS_PYTHON="$QRDS_VENV_PYTHON"
export PATH="$QRDS_VENV_SCRIPTS:$PATH"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
python() { "$QRDS_PYTHON" "$@"; }
python3() { "$QRDS_PYTHON" "$@"; }
export -f python
export -f python3
# QRDS_MANAGED_VENV_PYTHON_BOOTSTRAP_END

set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
PROJECT_ROOT="$REPO_ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/evidence_stack"
PREFERRED_PORT="${QRDS_PORT:-${PORT:-8132}}"

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

bash "$REPO_ROOT/qrds_evidence_stack.sh" "${GEN_ARGS[@]}"

if [[ "$OUTPUT_DIR" = /* ]]; then
  SERVE_DIR="$OUTPUT_DIR"
else
  SERVE_DIR="$PROJECT_ROOT/$OUTPUT_DIR"
fi
SERVE_DIR="$(cd "$SERVE_DIR" && pwd)"

if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS STACK] ERROR: index.html not found in $SERVE_DIR" >&2
  exit 1
fi

PORT_TO_USE="$(python - "$PREFERRED_PORT" <<'PYPORT'
import socket
import sys
preferred = int(sys.argv[1])
for port in range(preferred, preferred + 250):
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
PYPORT
)"

cat <<EOF

[QRDS STACK] Evidence Stack site ready.
[QRDS STACK] Serve directory: $SERVE_DIR
[QRDS STACK] Port: $PORT_TO_USE

Codespaces:
  Ports -> $PORT_TO_USE -> Open in Browser / Open Preview

Stop server with Ctrl+C.
EOF

cd "$SERVE_DIR"
exec python -m http.server "$PORT_TO_USE" --bind 0.0.0.0
