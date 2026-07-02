#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/dataset_evidence_explorer"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
SCAN_REPORT=""
MAX_FILES="150"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --scan-report) SCAN_REPORT="$2"; shift 2 ;;
    --max-files) MAX_FILES="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$SCAN_REPORT" ]]; then
  # Refresh 9K scanner when available, without starting its server.
  if [[ -x "$ROOT/qrds_dataset_evidence_scan.sh" ]]; then
    echo "[QRDS 9L] Refreshing 9K Dataset Evidence Scanner before Explorer..."
    bash "$ROOT/qrds_dataset_evidence_scan.sh" --output-dir artifacts/dataset_evidence_scan --symbols "$SYMBOLS" || true
  fi
  for candidate in \
    "$ROOT/crypto_decision_lab/artifacts/dataset_evidence_scan/dataset_evidence_scan.json" \
    "$ROOT/crypto_decision_lab/artifacts/dataset_evidence_scan/dataset_evidence_scan_gate.json" \
    "$ROOT/crypto_decision_lab/artifacts/dataset_evidence_scan/dataset_evidence_scanner.json" \
    "$ROOT/crypto_decision_lab/artifacts/dataset_evidence_scan/dataset_evidence_scanner_gate.json"; do
    if [[ -f "$candidate" ]]; then SCAN_REPORT="$candidate"; break; fi
  done
fi
ARGS=(--output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --max-files "$MAX_FILES")
if [[ -n "$SCAN_REPORT" ]]; then ARGS+=(--scan-report "$SCAN_REPORT"); fi
bash "$ROOT/qrds_dataset_evidence_explorer.sh" "${ARGS[@]}"
SERVE_DIR="$ROOT/crypto_decision_lab/$OUTPUT_DIR"
PORT=""
for p in $(seq 8138 8199); do
  if ! python - <<PY >/dev/null 2>&1
import socket
s=socket.socket();
try:
    s.bind(('0.0.0.0',$p)); s.close()
except OSError:
    raise SystemExit(1)
PY
  then
    continue
  fi
  PORT="$p"; break
done
if [[ -z "$PORT" ]]; then echo "[QRDS 9L] ERROR: no free port found" >&2; exit 1; fi
echo
echo "[QRDS 9L] Dataset Evidence Explorer site ready."
echo "[QRDS 9L] Serve directory: $SERVE_DIR"
echo "[QRDS 9L] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
