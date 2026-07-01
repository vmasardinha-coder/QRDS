#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$ROOT_DIR/crypto_decision_lab"
OUTPUT_DIR="artifacts/evidence_remediation"
SYMBOLS="BTC-USDT"
REPORTS=""
PORT=""
REFRESH_STACK=1
REVIEWER="Victor"
REVIEW_STATE="UNDER_REVIEW"
PAPER_DAYS="30"
PAPER_RUNS="20"
SIMULATED_FILL_RATE="0.95"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    --reports)
      REPORTS="$2"; shift 2 ;;
    --port)
      PORT="$2"; shift 2 ;;
    --no-refresh-stack)
      REFRESH_STACK=0; shift ;;
    --reviewer)
      REVIEWER="$2"; shift 2 ;;
    --review-state)
      REVIEW_STATE="$2"; shift 2 ;;
    --paper-days)
      PAPER_DAYS="$2"; shift 2 ;;
    --paper-runs)
      PAPER_RUNS="$2"; shift 2 ;;
    --simulated-fill-rate)
      SIMULATED_FILL_RATE="$2"; shift 2 ;;
    *)
      echo "[QRDS 8T] Unknown argument: $1" >&2
      exit 2 ;;
  esac
done

cd "$ROOT_DIR"

join_reports() {
  local IFS=','
  echo "$*"
}

if [[ "$REFRESH_STACK" == "1" && -z "$REPORTS" ]]; then
  echo "[QRDS 8T] Refreshing upstream research gates before remediation plan..."

  if [[ -x "$ROOT_DIR/qrds_evidence_quality.sh" ]]; then
    bash "$ROOT_DIR/qrds_evidence_quality.sh" --output-dir artifacts/evidence_quality --symbols "$SYMBOLS" >/tmp/qrds_8t_8l.log
  else
    echo "[QRDS 8T] Missing qrds_evidence_quality.sh; continuing with available artifacts."
  fi

  if [[ -x "$ROOT_DIR/qrds_evidence_drilldown.sh" && -f "$LAB_DIR/artifacts/evidence_quality/evidence_quality_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_evidence_drilldown.sh" --output-dir artifacts/evidence_drilldown --evidence-report artifacts/evidence_quality/evidence_quality_gate.json >/tmp/qrds_8t_8m.log
  fi

  if [[ -x "$ROOT_DIR/qrds_evidence_timeline.sh" && -f "$LAB_DIR/artifacts/evidence_quality/evidence_quality_gate.json" && -f "$LAB_DIR/artifacts/evidence_drilldown/evidence_drilldown_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_evidence_timeline.sh" \
      --output-dir artifacts/evidence_timeline \
      --reports artifacts/evidence_quality/evidence_quality_gate.json,artifacts/evidence_drilldown/evidence_drilldown_gate.json >/tmp/qrds_8t_8n.log
  fi

  if [[ -x "$ROOT_DIR/qrds_research_promotion.sh" && -f "$LAB_DIR/artifacts/evidence_timeline/evidence_timeline_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_research_promotion.sh" \
      --output-dir artifacts/research_promotion \
      --reports artifacts/evidence_quality/evidence_quality_gate.json,artifacts/evidence_drilldown/evidence_drilldown_gate.json,artifacts/evidence_timeline/evidence_timeline_gate.json >/tmp/qrds_8t_8o.log
  fi

  if [[ -x "$ROOT_DIR/qrds_human_review.sh" && -f "$LAB_DIR/artifacts/research_promotion/research_promotion_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_human_review.sh" \
      --output-dir artifacts/human_review \
      --reports artifacts/evidence_quality/evidence_quality_gate.json,artifacts/evidence_drilldown/evidence_drilldown_gate.json,artifacts/evidence_timeline/evidence_timeline_gate.json,artifacts/research_promotion/research_promotion_gate.json \
      --review-state "$REVIEW_STATE" \
      --reviewer "$REVIEWER" >/tmp/qrds_8t_8p.log
  fi

  if [[ -x "$ROOT_DIR/qrds_oos_validation.sh" && -f "$LAB_DIR/artifacts/human_review/human_review_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_oos_validation.sh" \
      --output-dir artifacts/oos_validation \
      --reports artifacts/evidence_quality/evidence_quality_gate.json,artifacts/evidence_drilldown/evidence_drilldown_gate.json,artifacts/evidence_timeline/evidence_timeline_gate.json,artifacts/research_promotion/research_promotion_gate.json,artifacts/human_review/human_review_gate.json >/tmp/qrds_8t_8q.log
  fi

  if [[ -x "$ROOT_DIR/qrds_paper_trading.sh" && -f "$LAB_DIR/artifacts/oos_validation/oos_validation_gate.json" ]]; then
    bash "$ROOT_DIR/qrds_paper_trading.sh" \
      --output-dir artifacts/paper_trading \
      --reports artifacts/evidence_quality/evidence_quality_gate.json,artifacts/evidence_drilldown/evidence_drilldown_gate.json,artifacts/evidence_timeline/evidence_timeline_gate.json,artifacts/research_promotion/research_promotion_gate.json,artifacts/human_review/human_review_gate.json,artifacts/oos_validation/oos_validation_gate.json \
      --paper-days "$PAPER_DAYS" \
      --paper-runs "$PAPER_RUNS" \
      --simulated-fill-rate "$SIMULATED_FILL_RATE" \
      --cost-model-present \
      --paper-artifact-present \
      --acceptance-state UNDER_REVIEW >/tmp/qrds_8t_8r.log || true
  fi
fi

if [[ -z "$REPORTS" ]]; then
  declare -a CANDIDATES=(
    "$LAB_DIR/artifacts/evidence_quality/evidence_quality_gate.json"
    "$LAB_DIR/artifacts/evidence_drilldown/evidence_drilldown_gate.json"
    "$LAB_DIR/artifacts/evidence_timeline/evidence_timeline_gate.json"
    "$LAB_DIR/artifacts/research_promotion/research_promotion_gate.json"
    "$LAB_DIR/artifacts/human_review/human_review_gate.json"
    "$LAB_DIR/artifacts/oos_validation/oos_validation_gate.json"
    "$LAB_DIR/artifacts/paper_trading/paper_trading_gate.json"
  )
  REPORT_LIST=()
  for candidate in "${CANDIDATES[@]}"; do
    if [[ -f "$candidate" ]]; then
      rel="${candidate#$LAB_DIR/}"
      REPORT_LIST+=("$rel")
    fi
  done
  REPORTS="$(join_reports "${REPORT_LIST[@]}")"
fi

echo "[QRDS 8T] Building evidence remediation plan..."
if [[ -n "$REPORTS" ]]; then
  bash "$ROOT_DIR/qrds_evidence_remediation.sh" --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --reports "$REPORTS"
else
  bash "$ROOT_DIR/qrds_evidence_remediation.sh" --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS"
fi

SERVE_DIR="$LAB_DIR/$OUTPUT_DIR"
if [[ ! -f "$SERVE_DIR/index.html" ]]; then
  echo "[QRDS 8T] Expected index not found: $SERVE_DIR/index.html" >&2
  exit 1
fi

if [[ -z "$PORT" ]]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8133, 8199):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("No free port found in range 8133-8198")
PY
)"
fi

echo
echo "[QRDS 8T] Evidence Remediation Plan site ready."
echo "[QRDS 8T] Serve directory: $SERVE_DIR"
echo "[QRDS 8T] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."
cd "$SERVE_DIR"
python -m http.server "$PORT" --bind 0.0.0.0
