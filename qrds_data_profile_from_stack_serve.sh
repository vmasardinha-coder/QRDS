#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUTPUT_DIR="artifacts/data_profile"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
PORT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "[QRDS 9G] Refreshing upstream stack before Data Profile Pack..."
if [[ -x "$ROOT/qrds_evidence_stack.sh" ]]; then
  "$ROOT/qrds_evidence_stack.sh" --output-dir artifacts/evidence_stack --symbols "$SYMBOLS" >/dev/null || true
fi
if [[ -x "$ROOT/qrds_dataset_manifest_from_stack.sh" ]]; then
  "$ROOT/qrds_dataset_manifest_from_stack.sh" >/dev/null || true
fi

CANONICAL=(
"$PROJECT/artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json"
"$PROJECT/artifacts/evidence_stack/evidence_drilldown/evidence_drilldown_gate.json"
"$PROJECT/artifacts/evidence_stack/evidence_timeline/evidence_timeline_gate.json"
"$PROJECT/artifacts/evidence_stack/research_promotion/research_promotion_gate.json"
"$PROJECT/artifacts/evidence_stack/human_review/human_review_gate.json"
"$PROJECT/artifacts/evidence_stack/oos_validation/oos_validation_gate.json"
"$PROJECT/artifacts/evidence_stack/paper_trading/paper_trading_gate.json"
"$PROJECT/artifacts/evidence_stack/risk_model/risk_model_gate.json"
"$PROJECT/artifacts/operational_security/operational_security_gate.json"
"$PROJECT/artifacts/data_coverage/data_coverage_gate.json"
"$PROJECT/artifacts/data_quality/data_quality_gate.json"
"$PROJECT/artifacts/data_audit/data_audit_pack.json"
"$PROJECT/artifacts/dataset_manifest/dataset_manifest_pack.json"
"$PROJECT/artifacts/dataset_manifest/dataset_manifest_gate.json"
)
REPORTS=""
MANIFESTS=""
for f in "${CANONICAL[@]}"; do
  if [[ -f "$f" ]]; then
    if [[ -z "$REPORTS" ]]; then REPORTS="$f"; else REPORTS="$REPORTS,$f"; fi
    case "$f" in
      *dataset_manifest*) if [[ -z "$MANIFESTS" ]]; then MANIFESTS="$f"; else MANIFESTS="$MANIFESTS,$f"; fi ;;
    esac
  fi
done

echo "[QRDS 9G] Explicit reports found: $REPORTS"
cd "$PROJECT"
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m crypto_decision_lab.cli.data_profile \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS" \
  --manifest-reports "$MANIFESTS"

SERVE_DIR="$PROJECT/$OUTPUT_DIR"
if [[ -z "$PORT" ]]; then
  PORT=$(python - <<'PY'
import socket
for port in range(8138, 8189):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
            print(port)
            break
        except OSError:
            pass
PY
)
fi

echo ""
echo "[QRDS 9G] Data Profile Pack site ready."
echo "[QRDS 9G] Serve directory: $SERVE_DIR"
echo "[QRDS 9G] Port: $PORT"
echo ""
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo ""
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
