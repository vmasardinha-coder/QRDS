#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUTPUT_DIR="artifacts/workspace_housekeeping"
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

bash qrds_housekeeping.sh "${ARGS[@]}"
SERVE_DIR="$(cd crypto_decision_lab && python - <<PY
from pathlib import Path
out = Path('${OUTPUT_DIR}')
if not out.is_absolute():
    out = Path.cwd() / out
print(out.resolve())
PY
)"

PORT="${QRDS_PORT:-}"
if [[ -z "${PORT}" ]]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8132, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("No free port found in 8132-8198")
PY
)"
fi

echo
echo "[QRDS 9A] Workspace Housekeeping site ready."
echo "[QRDS 9A] Serve directory: ${SERVE_DIR}"
echo "[QRDS 9A] Port: ${PORT}"
echo
echo "Codespaces:"
echo "  Ports -> ${PORT} -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "${SERVE_DIR}"
python -m http.server "${PORT}" --bind 0.0.0.0
