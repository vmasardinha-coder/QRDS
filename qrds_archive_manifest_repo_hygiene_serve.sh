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
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/archive_manifest_repo_hygiene"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
echo "[QRDS 9X] Building Archive Manifest / Repo Hygiene Index..."
bash "$ROOT/qrds_archive_manifest_repo_hygiene.sh" "$OUT"
PORT="$(python - <<'PY'
import socket
for port in range(8135, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind(('0.0.0.0', port))
        except OSError: continue
        print(port); break
else: raise SystemExit('NO_FREE_PORT')
PY
)"
echo; echo "[QRDS 9X] Archive Manifest / Repo Hygiene Index ready."; echo "[QRDS 9X] Serve directory: $OUT"; echo "[QRDS 9X] Port: $PORT"; echo; echo "Codespaces:"; echo "  Ports -> $PORT -> Open in Browser / Open Preview"; echo; echo "Stop server with Ctrl+C."
cd "$OUT"; python -m http.server "$PORT" --bind 0.0.0.0
