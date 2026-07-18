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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"

STACK_OUTPUT_DIR="artifacts/evidence_stack"
RISK_OUTPUT_DIR="artifacts/risk_model"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REVIEW_STATE="${QRDS_REVIEW_STATE:-UNDER_REVIEW}"
REVIEWER="${QRDS_REVIEWER:-Victor}"
PAPER_DAYS="${QRDS_PAPER_DAYS:-30}"
PAPER_RUNS="${QRDS_PAPER_RUNS:-20}"
SIMULATED_FILL_RATE="${QRDS_SIMULATED_FILL_RATE:-0.95}"
ACCEPTANCE_STATE="${QRDS_ACCEPTANCE_STATE:-UNDER_REVIEW}"
RUN_STACK=1

usage() {
  cat <<'USAGE'
QRDS Risk Model from Evidence Stack Serve

Generates the 8L → 8R evidence stack first, then runs the 8U Risk Model Gate
using the generated stack reports. Research-only; cannot unlock operational use.

Usage:
  bash qrds_risk_model_from_stack_serve.sh

Options:
  --stack-output-dir DIR        Default: artifacts/evidence_stack
  --output-dir DIR              Risk model output. Default: artifacts/risk_model
  --symbols LIST                Default: BTC-USDT,ETH-USDT,SOL-USDT
  --review-state STATE          Passed to the stack human review gate. Default: UNDER_REVIEW
  --reviewer NAME               Passed to the stack human review gate. Default: Victor
  --paper-days N                Passed to the stack paper gate. Default: 30
  --paper-runs N                Passed to the stack paper gate. Default: 20
  --simulated-fill-rate X       Passed to the stack paper gate. Default: 0.95
  --acceptance-state STATE      Passed to the stack paper gate. Default: UNDER_REVIEW
  --skip-stack-refresh          Do not regenerate 8L → 8R; only read existing stack artifacts.
  -h, --help                    Show help.

Codespaces:
  The script prints the port. Open: Ports -> porta indicada -> Open in Browser / Open Preview
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack-output-dir) STACK_OUTPUT_DIR="${2:?missing value for --stack-output-dir}"; shift 2 ;;
    --stack-output-dir=*) STACK_OUTPUT_DIR="${1#--stack-output-dir=}"; shift ;;
    --output-dir) RISK_OUTPUT_DIR="${2:?missing value for --output-dir}"; shift 2 ;;
    --output-dir=*) RISK_OUTPUT_DIR="${1#--output-dir=}"; shift ;;
    --symbols) SYMBOLS="${2:?missing value for --symbols}"; shift 2 ;;
    --symbols=*) SYMBOLS="${1#--symbols=}"; shift ;;
    --review-state) REVIEW_STATE="${2:?missing value for --review-state}"; shift 2 ;;
    --review-state=*) REVIEW_STATE="${1#--review-state=}"; shift ;;
    --reviewer) REVIEWER="${2:?missing value for --reviewer}"; shift 2 ;;
    --reviewer=*) REVIEWER="${1#--reviewer=}"; shift ;;
    --paper-days) PAPER_DAYS="${2:?missing value for --paper-days}"; shift 2 ;;
    --paper-days=*) PAPER_DAYS="${1#--paper-days=}"; shift ;;
    --paper-runs) PAPER_RUNS="${2:?missing value for --paper-runs}"; shift 2 ;;
    --paper-runs=*) PAPER_RUNS="${1#--paper-runs=}"; shift ;;
    --simulated-fill-rate) SIMULATED_FILL_RATE="${2:?missing value for --simulated-fill-rate}"; shift 2 ;;
    --simulated-fill-rate=*) SIMULATED_FILL_RATE="${1#--simulated-fill-rate=}"; shift ;;
    --acceptance-state) ACCEPTANCE_STATE="${2:?missing value for --acceptance-state}"; shift 2 ;;
    --acceptance-state=*) ACCEPTANCE_STATE="${1#--acceptance-state=}"; shift ;;
    --skip-stack-refresh) RUN_STACK=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[QRDS 8U] ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[QRDS 8U] ERROR: crypto_decision_lab project not found under $ROOT_DIR" >&2
  exit 1
fi

if [[ "$RUN_STACK" == "1" ]]; then
  if [[ ! -x "$ROOT_DIR/qrds_evidence_stack.sh" ]]; then
    echo "[QRDS 8U] ERROR: qrds_evidence_stack.sh not found/executable. Install Sprint 8S first." >&2
    exit 1
  fi
  echo "[QRDS 8U] Refreshing upstream evidence stack 8L -> 8R..."
  bash "$ROOT_DIR/qrds_evidence_stack.sh" \
    --output-dir "$STACK_OUTPUT_DIR" \
    --symbols "$SYMBOLS" \
    --review-state "$REVIEW_STATE" \
    --reviewer "$REVIEWER" \
    --paper-days "$PAPER_DAYS" \
    --paper-runs "$PAPER_RUNS" \
    --simulated-fill-rate "$SIMULATED_FILL_RATE" \
    --acceptance-state "$ACCEPTANCE_STATE"
else
  echo "[QRDS 8U] Skipping upstream stack refresh by request."
fi

report_path() {
  local rel="$1"
  if [[ "$STACK_OUTPUT_DIR" = /* ]]; then
    printf '%s/%s' "$STACK_OUTPUT_DIR" "$rel"
  else
    # qrds_risk_model.sh executes from crypto_decision_lab, so relative report
    # paths must be relative to crypto_decision_lab, not to the repo root.
    printf '%s/%s' "$STACK_OUTPUT_DIR" "$rel"
  fi
}

REPORTS=(
  "$(report_path 'evidence_quality/evidence_quality_gate.json')"
  "$(report_path 'evidence_drilldown/evidence_drilldown_gate.json')"
  "$(report_path 'evidence_timeline/evidence_timeline_gate.json')"
  "$(report_path 'research_promotion/research_promotion_gate.json')"
  "$(report_path 'human_review/human_review_gate.json')"
  "$(report_path 'oos_validation/oos_validation_gate.json')"
  "$(report_path 'paper_trading/paper_trading_gate.json')"
)

EXISTING=()
for report in "${REPORTS[@]}"; do
  if [[ "$report" = /* ]]; then
    check_path="$report"
  else
    check_path="$PROJECT_DIR/$report"
  fi
  if [[ -f "$check_path" ]]; then
    EXISTING+=("$report")
  else
    echo "[QRDS 8U] WARN: missing upstream report: $check_path" >&2
  fi
done

REPORTS_CSV="$(IFS=,; echo "${EXISTING[*]}")"

cat <<EOF
[QRDS 8U] Upstream reports found: ${#EXISTING[@]}/7
[QRDS 8U] Stack output dir: $STACK_OUTPUT_DIR
[QRDS 8U] Risk output dir: $RISK_OUTPUT_DIR
[QRDS 8U] Symbols: $SYMBOLS
[QRDS 8U] Scope: research-only; no signal, no recommendation, no order.
EOF

exec bash "$ROOT_DIR/qrds_risk_model_serve.sh" \
  --output-dir "$RISK_OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS_CSV" \
  --max-portfolio-drawdown-pct 20 \
  --max-symbol-exposure-pct 35 \
  --daily-loss-limit-pct 5 \
  --stress-loss-limit-pct 30 \
  --kill-switch-present \
  --liquidity-check-present \
  --cost-model-present \
  --risk-artifact-present \
  --risk-state UNDER_REVIEW
