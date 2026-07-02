#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

OUTPUT_DIR="artifacts/data_coverage"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
PORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    --port)
      PORT="$2"; shift 2 ;;
    *)
      echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9B] Refreshing evidence stack before Data Coverage Gate..."
if [[ -x "./qrds_evidence_stack.sh" ]]; then
  bash ./qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/tmp/qrds_9b_stack_refresh.log 2>&1 || {
    cat /tmp/qrds_9b_stack_refresh.log >&2
    echo "[QRDS 9B] ERROR: evidence stack refresh failed." >&2
    exit 1
  }
else
  echo "[QRDS 9B] WARNING: qrds_evidence_stack.sh not found; using existing artifacts only." >&2
fi

# Canonical, de-duplicated report chain. Prefer artifacts produced by the stack
# runner, then include later gates that currently live outside the stack runner.
CANDIDATES=(
  "crypto_decision_lab/artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/evidence_drilldown/evidence_drilldown_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/evidence_timeline/evidence_timeline_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/research_promotion/research_promotion_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/human_review/human_review_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/oos_validation/oos_validation_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/paper_trading/paper_trading_gate.json"
  "crypto_decision_lab/artifacts/evidence_stack/risk_model/risk_model_gate.json"
  "crypto_decision_lab/artifacts/operational_security/operational_security_gate.json"
)

REPORTS=""
for f in "${CANDIDATES[@]}"; do
  if [[ -f "$f" ]]; then
    if [[ -z "$REPORTS" ]]; then
      REPORTS="$f"
    else
      REPORTS="$REPORTS,$f"
    fi
  fi
done

if [[ -z "$REPORTS" ]]; then
  echo "[QRDS 9B] WARNING: no explicit prior reports found; gate will block promotion." >&2
else
  echo "[QRDS 9B] Explicit reports found: $REPORTS"
fi

cd crypto_decision_lab
PYTHONPATH="$PWD/src" python -m crypto_decision_lab.cli.data_coverage \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  ${REPORTS:+--reports "$REPORTS"}

SERVE_DIR="$PWD/$OUTPUT_DIR"
if [[ ! -d "$SERVE_DIR" ]]; then
  echo "[QRDS 9B] ERROR: serve dir not found: $SERVE_DIR" >&2
  exit 1
fi

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
else:
    raise SystemExit("no free port found")
PY
)"
fi

echo
echo "[QRDS 9B] Data Coverage Gate site ready."
echo "[QRDS 9B] Serve directory: $SERVE_DIR"
echo "[QRDS 9B] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
