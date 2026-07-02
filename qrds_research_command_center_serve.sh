#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
OUTPUT_DIR="artifacts/research_command_center"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REPORTS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --reports) REPORTS="$2"; shift 2 ;;
    *) echo "[QRDS 9J] Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$REPORTS" ]]; then
  echo "[QRDS 9J] Discovering canonical reports for Research Command Center..."
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
    "crypto_decision_lab/artifacts/data_coverage/data_coverage_gate.json"
    "crypto_decision_lab/artifacts/data_quality/data_quality_gate.json"
    "crypto_decision_lab/artifacts/data_audit/data_audit_gate.json"
    "crypto_decision_lab/artifacts/dataset_manifest/dataset_manifest_pack.json"
    "crypto_decision_lab/artifacts/data_profile/data_profile_pack.json"
    "crypto_decision_lab/artifacts/data_readiness/data_readiness_matrix.json"
    "crypto_decision_lab/artifacts/data_gap_remediation/data_gap_remediation_plan.json"
    "crypto_decision_lab/artifacts/acceptance_runner/acceptance_runner.json"
  )
  FOUND=()
  for f in "${CANDIDATES[@]}"; do
    [[ -f "$f" ]] && FOUND+=("$f")
  done
  IFS=,; REPORTS="${FOUND[*]}"; unset IFS
fi

echo "[QRDS 9J] Reports: ${REPORTS:-NONE}"
bash "$REPO_ROOT/qrds_research_command_center.sh" --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"

SERVE_DIR="$REPO_ROOT/crypto_decision_lab/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 9J] ERROR: index.html not found in $SERVE_DIR" >&2
  exit 1
fi

PORT="$(python - <<'PY'
import socket
for port in range(8140, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("no free port")
PY
)"

echo
printf '[QRDS 9J] Research Command Center ready.\n'
printf '[QRDS 9J] Serve directory: %s\n' "$SERVE_DIR"
printf '[QRDS 9J] Port: %s\n\n' "$PORT"
printf 'Codespaces:\n  Ports -> %s -> Open in Browser / Open Preview\n\n' "$PORT"
printf 'Stop server with Ctrl+C.\n'
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
