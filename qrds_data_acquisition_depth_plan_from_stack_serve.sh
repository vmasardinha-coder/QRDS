#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$REPO_ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/data_acquisition_depth_plan"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
MIN_ROWS="5000"
INTERVAL="1h"
PORT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --min-rows-per-symbol) MIN_ROWS="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "[QRDS 9N] Unknown arg: $1" >&2; exit 2 ;;
  esac
done

cd "$REPO_ROOT"
mkdir -p "$PROJECT_DIR/$OUTPUT_DIR"

REPORTS=()
for f in \
  "$PROJECT_DIR/artifacts/dataset_evidence_scan/dataset_evidence_scan_index.json" \
  "$PROJECT_DIR/artifacts/dataset_evidence_scan/dataset_evidence_scan.json" \
  "$PROJECT_DIR/artifacts/dataset_evidence_explorer/dataset_evidence_explorer_index.json" \
  "$PROJECT_DIR/artifacts/dataset_evidence_explorer/dataset_evidence_explorer.json" \
  "$PROJECT_DIR/artifacts/dataset_depth_requirements/dataset_depth_requirements_index.json" \
  "$PROJECT_DIR/artifacts/dataset_depth_requirements/dataset_depth_requirements_gate.json"; do
  if [ -f "$f" ]; then
    REPORTS+=("$f")
  fi
done

REPORT_ARG=""
if [ ${#REPORTS[@]} -gt 0 ]; then
  REPORT_ARG=$(IFS=,; echo "${REPORTS[*]}")
fi

echo "[QRDS 9N] Explicit reports found: $REPORT_ARG"
cd "$PROJECT_DIR"
python -m crypto_decision_lab.cli.data_acquisition_depth_plan \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORT_ARG" \
  --min-rows-per-symbol "$MIN_ROWS" \
  --interval "$INTERVAL"

if [ -z "$PORT" ]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8133, 8199):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
            print(port)
            break
        except OSError:
            continue
PY
)
fi

SERVE_DIR="$PROJECT_DIR/$OUTPUT_DIR"
echo
echo "[QRDS 9N] Data Acquisition Depth Plan site ready."
echo "[QRDS 9N] Serve directory: $SERVE_DIR"
echo "[QRDS 9N] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
