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

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/research_book_reader"
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  if [[ "${ARGS[$i]}" == "--output-dir" && $((i+1)) -lt ${#ARGS[@]} ]]; then
    OUTPUT_DIR="${ARGS[$((i+1))]}"
  fi
done
python -m crypto_decision_lab.cli.research_book_reader "$@"
if [[ ! -f "$OUTPUT_DIR/index.html" ]]; then
  echo "[QRDS 8Z] ERROR: $OUTPUT_DIR/index.html not found" >&2
  exit 1
fi
PORT="${QRDS_PORT:-}"
if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8136, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
PY
)"
fi
if [[ -z "$PORT" ]]; then
  echo "[QRDS 8Z] ERROR: no free port found" >&2
  exit 1
fi
ABS_DIR="$(cd "$OUTPUT_DIR" && pwd)"
echo
echo "[QRDS 8Z] Research Book Reader ready."
echo "[QRDS 8Z] Serve directory: $ABS_DIR"
echo "[QRDS 8Z] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Expected top:"
echo "  Gate answer: RESEARCH_BOOK_READER_PORTAL_READY_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"
echo "  Policy lock: ACTIVE"
echo "  Mode: INTERACTIVE_RESEARCH_ONLY"
echo "  Planned chapters: 20"
echo "  PDF: QRDS_RESEARCH_BOOK_READER.pdf"
echo
echo "Stop server with Ctrl+C."
cd "$ABS_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
