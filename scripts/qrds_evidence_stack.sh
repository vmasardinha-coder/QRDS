#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$REPO_ROOT/crypto_decision_lab"

OUTPUT_DIR="artifacts/evidence_stack"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
REVIEW_STATE="${QRDS_REVIEW_STATE:-UNDER_REVIEW}"
REVIEWER="${QRDS_REVIEWER:-Victor}"
PAPER_DAYS="${QRDS_PAPER_DAYS:-30}"
PAPER_RUNS="${QRDS_PAPER_RUNS:-20}"
SIMULATED_FILL_RATE="${QRDS_SIMULATED_FILL_RATE:-0.95}"
ACCEPTANCE_STATE="${QRDS_ACCEPTANCE_STATE:-UNDER_REVIEW}"
COST_MODEL_PRESENT=1
PAPER_ARTIFACT_PRESENT=1
SKIP_PAPER=0
DRY_RUN="${QRDS_STACK_DRY_RUN:-0}"

usage() {
  cat <<'USAGE'
QRDS Evidence Stack Runner v1

Runs the research-only evidence gate stack in the correct order and passes
prior JSON reports forward automatically.

Usage:
  bash qrds_evidence_stack.sh \
    --output-dir artifacts/evidence_stack \
    --symbols BTC-USDT,ETH-USDT,SOL-USDT

Options:
  --output-dir DIR             Stack output directory under crypto_decision_lab/ when relative.
  --symbols LIST               Comma-separated research symbols.
  --review-state STATE         Human review state for the 8P gate. Default: UNDER_REVIEW.
  --reviewer NAME              Human reviewer label. Default: Victor.
  --paper-days N               Simulated/paper observation days for 8R. Default: 30.
  --paper-runs N               Simulated/paper run count for 8R. Default: 20.
  --simulated-fill-rate X      Simulated fill-rate metadata for 8R. Default: 0.95.
  --acceptance-state STATE     Paper acceptance state for 8R. Default: UNDER_REVIEW.
  --no-cost-model-present      Do not pass --cost-model-present to 8R.
  --no-paper-artifact-present  Do not pass --paper-artifact-present to 8R.
  --skip-paper                 Skip 8R even if installed.
  --dry-run                    Print the planned sequence without running gates.
  -h, --help                   Show this help.

Safety: research-only. This runner cannot produce orders, signals,
recommendations, allocation, position sizing, or operational decisions.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"; shift 2 ;;
    --output-dir=*)
      OUTPUT_DIR="${1#--output-dir=}"; shift ;;
    --symbols)
      SYMBOLS="${2:?missing value for --symbols}"; shift 2 ;;
    --symbols=*)
      SYMBOLS="${1#--symbols=}"; shift ;;
    --review-state)
      REVIEW_STATE="${2:?missing value for --review-state}"; shift 2 ;;
    --review-state=*)
      REVIEW_STATE="${1#--review-state=}"; shift ;;
    --reviewer)
      REVIEWER="${2:?missing value for --reviewer}"; shift 2 ;;
    --reviewer=*)
      REVIEWER="${1#--reviewer=}"; shift ;;
    --paper-days)
      PAPER_DAYS="${2:?missing value for --paper-days}"; shift 2 ;;
    --paper-days=*)
      PAPER_DAYS="${1#--paper-days=}"; shift ;;
    --paper-runs)
      PAPER_RUNS="${2:?missing value for --paper-runs}"; shift 2 ;;
    --paper-runs=*)
      PAPER_RUNS="${1#--paper-runs=}"; shift ;;
    --simulated-fill-rate)
      SIMULATED_FILL_RATE="${2:?missing value for --simulated-fill-rate}"; shift 2 ;;
    --simulated-fill-rate=*)
      SIMULATED_FILL_RATE="${1#--simulated-fill-rate=}"; shift ;;
    --acceptance-state)
      ACCEPTANCE_STATE="${2:?missing value for --acceptance-state}"; shift 2 ;;
    --acceptance-state=*)
      ACCEPTANCE_STATE="${1#--acceptance-state=}"; shift ;;
    --no-cost-model-present)
      COST_MODEL_PRESENT=0; shift ;;
    --no-paper-artifact-present)
      PAPER_ARTIFACT_PRESENT=0; shift ;;
    --skip-paper)
      SKIP_PAPER=1; shift ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[QRDS STACK] ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

if [[ ! -d "$PROJECT_ROOT" ]]; then
  echo "[QRDS STACK] ERROR: crypto_decision_lab project not found under $REPO_ROOT" >&2
  exit 1
fi

if [[ "$OUTPUT_DIR" = /* ]]; then
  STACK_DIR="$OUTPUT_DIR"
  EQ_OUT="$STACK_DIR/evidence_quality"
  DRILL_OUT="$STACK_DIR/evidence_drilldown"
  TIMELINE_OUT="$STACK_DIR/evidence_timeline"
  PROMO_OUT="$STACK_DIR/research_promotion"
  HUMAN_OUT="$STACK_DIR/human_review"
  OOS_OUT="$STACK_DIR/oos_validation"
  PAPER_OUT="$STACK_DIR/paper_trading"
  HUB_OUT="$STACK_DIR"
else
  STACK_DIR="$PROJECT_ROOT/$OUTPUT_DIR"
  EQ_OUT="$OUTPUT_DIR/evidence_quality"
  DRILL_OUT="$OUTPUT_DIR/evidence_drilldown"
  TIMELINE_OUT="$OUTPUT_DIR/evidence_timeline"
  PROMO_OUT="$OUTPUT_DIR/research_promotion"
  HUMAN_OUT="$OUTPUT_DIR/human_review"
  OOS_OUT="$OUTPUT_DIR/oos_validation"
  PAPER_OUT="$OUTPUT_DIR/paper_trading"
  HUB_OUT="$PROJECT_ROOT/$OUTPUT_DIR"
fi

mkdir -p "$STACK_DIR"
ITEMS_TSV="$STACK_DIR/evidence_stack_items.tsv"
: > "$ITEMS_TSV"

rel_report() {
  local out_dir="$1"
  local report_file="$2"
  printf '%s/%s' "$out_dir" "$report_file"
}

append_item() {
  local gate_id="$1"
  local title="$2"
  local report_path_for_cli="$3"
  local html_rel="$4"
  local status="$5"
  printf '%s\t%s\t%s\t%s\t%s\n' "$gate_id" "$title" "$report_path_for_cli" "$html_rel" "$status" >> "$ITEMS_TSV"
}

run_or_plan() {
  local label="$1"
  local script_name="$2"
  shift 2
  if [[ ! -x "$REPO_ROOT/$script_name" ]]; then
    echo "[QRDS STACK] SKIP $label: $script_name not found or not executable."
    return 127
  fi
  echo
  echo "[QRDS STACK] Running $label..."
  echo "  bash $script_name $*"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  bash "$REPO_ROOT/$script_name" "$@"
}

EQ_REPORT="$(rel_report "$EQ_OUT" evidence_quality_gate.json)"
DRILL_REPORT="$(rel_report "$DRILL_OUT" evidence_drilldown_gate.json)"
TIMELINE_REPORT="$(rel_report "$TIMELINE_OUT" evidence_timeline_gate.json)"
PROMO_REPORT="$(rel_report "$PROMO_OUT" research_promotion_gate.json)"
HUMAN_REPORT="$(rel_report "$HUMAN_OUT" human_review_gate.json)"
OOS_REPORT="$(rel_report "$OOS_OUT" oos_validation_gate.json)"
PAPER_REPORT="$(rel_report "$PAPER_OUT" paper_trading_gate.json)"

cat <<EOF
[QRDS STACK] Evidence Stack Runner v1
[QRDS STACK] Repo: $REPO_ROOT
[QRDS STACK] Stack output: $STACK_DIR
[QRDS STACK] Symbols: $SYMBOLS
[QRDS STACK] Scope: research-only; no signal, no recommendation, no order.
EOF

run_or_plan "8L Evidence Quality" "qrds_evidence_quality.sh" \
  --output-dir "$EQ_OUT" \
  --symbols "$SYMBOLS"
append_item "8L" "Evidence Quality Gate" "$EQ_REPORT" "evidence_quality/index.html" "REQUESTED"

run_or_plan "8M Evidence Drilldown" "qrds_evidence_drilldown.sh" \
  --output-dir "$DRILL_OUT" \
  --evidence-report "$EQ_REPORT"
append_item "8M" "Evidence Drilldown Gate" "$DRILL_REPORT" "evidence_drilldown/index.html" "REQUESTED"

run_or_plan "8N Evidence Timeline" "qrds_evidence_timeline.sh" \
  --output-dir "$TIMELINE_OUT" \
  --reports "$EQ_REPORT,$DRILL_REPORT"
append_item "8N" "Evidence Timeline Gate" "$TIMELINE_REPORT" "evidence_timeline/index.html" "REQUESTED"

run_or_plan "8O Research Promotion" "qrds_research_promotion.sh" \
  --output-dir "$PROMO_OUT" \
  --reports "$EQ_REPORT,$DRILL_REPORT,$TIMELINE_REPORT"
append_item "8O" "Research Promotion Gate" "$PROMO_REPORT" "research_promotion/index.html" "REQUESTED"

run_or_plan "8P Human Review / Policy Lock" "qrds_human_review.sh" \
  --output-dir "$HUMAN_OUT" \
  --reports "$EQ_REPORT,$DRILL_REPORT,$TIMELINE_REPORT,$PROMO_REPORT" \
  --review-state "$REVIEW_STATE" \
  --reviewer "$REVIEWER"
append_item "8P" "Human Review / Policy Lock Gate" "$HUMAN_REPORT" "human_review/index.html" "REQUESTED"

run_or_plan "8Q Out-of-Sample Validation" "qrds_oos_validation.sh" \
  --output-dir "$OOS_OUT" \
  --reports "$EQ_REPORT,$DRILL_REPORT,$TIMELINE_REPORT,$PROMO_REPORT,$HUMAN_REPORT"
append_item "8Q" "Out-of-Sample Validation Gate" "$OOS_REPORT" "oos_validation/index.html" "REQUESTED"

if [[ "$SKIP_PAPER" == "1" ]]; then
  echo
  echo "[QRDS STACK] SKIP 8R Paper Trading: --skip-paper was requested."
  append_item "8R" "Paper Trading Gate" "$PAPER_REPORT" "paper_trading/index.html" "SKIPPED_BY_USER"
elif [[ -x "$REPO_ROOT/qrds_paper_trading.sh" ]]; then
  PAPER_ARGS=(
    --output-dir "$PAPER_OUT"
    --reports "$EQ_REPORT,$DRILL_REPORT,$TIMELINE_REPORT,$PROMO_REPORT,$HUMAN_REPORT,$OOS_REPORT"
    --paper-days "$PAPER_DAYS"
    --paper-runs "$PAPER_RUNS"
    --simulated-fill-rate "$SIMULATED_FILL_RATE"
    --acceptance-state "$ACCEPTANCE_STATE"
  )
  if [[ "$COST_MODEL_PRESENT" == "1" ]]; then PAPER_ARGS+=(--cost-model-present); fi
  if [[ "$PAPER_ARTIFACT_PRESENT" == "1" ]]; then PAPER_ARGS+=(--paper-artifact-present); fi
  run_or_plan "8R Paper Trading" "qrds_paper_trading.sh" "${PAPER_ARGS[@]}"
  append_item "8R" "Paper Trading Gate" "$PAPER_REPORT" "paper_trading/index.html" "REQUESTED"
else
  echo
  echo "[QRDS STACK] SKIP 8R Paper Trading: qrds_paper_trading.sh not installed yet. Run Sprint 8R first, then rerun this stack."
  append_item "8R" "Paper Trading Gate" "$PAPER_REPORT" "paper_trading/index.html" "MISSING_WRAPPER"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "[QRDS STACK] Dry run complete. No artifacts generated."
  exit 0
fi

python - "$STACK_DIR" "$ITEMS_TSV" "$SYMBOLS" <<'PYSTACK'
from __future__ import annotations

import hashlib
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

stack_dir = Path(sys.argv[1])
items_tsv = Path(sys.argv[2])
symbols = [item.strip().upper() for item in sys.argv[3].split(',') if item.strip()]

SAFETY_FLAGS: dict[str, bool | str] = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}


def project_root_from_stack(path: Path) -> Path:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    while current.name != "crypto_decision_lab" and current.parent != current:
        current = current.parent
    return current


def load_report(path_text: str) -> tuple[dict[str, Any] | None, str]:
    path = Path(path_text)
    if not path.is_absolute():
        path = project_root_from_stack(stack_dir) / path
    if not path.exists():
        return None, "MISSING"
    data = path.read_bytes()
    try:
        payload = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        return None, hashlib.sha256(data).hexdigest()
    return payload if isinstance(payload, dict) else None, hashlib.sha256(data).hexdigest()

rows: list[dict[str, Any]] = []
for line in items_tsv.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    gate_id, title, report_path, html_rel, requested_status = line.split("\t")
    payload, sha = load_report(report_path)
    if payload is None:
        gate_answer = "MISSING_OR_INVALID_REPORT"
        schema = "MISSING"
        ready = False
        score = 0.0
        status = requested_status if requested_status.startswith("SKIPPED") or requested_status.startswith("MISSING") else "MISSING_REPORT"
    else:
        gate_answer = str(payload.get("gate_answer", "UNKNOWN"))
        schema = str(payload.get("schema", "UNKNOWN"))
        ready = not gate_answer.startswith("NO_") and "FAIL" not in gate_answer and "MISSING" not in gate_answer
        raw_score = payload.get("mean_research_readiness_score", payload.get("mean_symbol_evidence_score", payload.get("mean_oos_score", payload.get("mean_latest_score", 0.0)))) or 0.0
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        status = "REPORT_PRESENT"
    rows.append({
        "gate_id": gate_id,
        "title": title,
        "report_path": report_path,
        "html_path": html_rel,
        "schema": schema,
        "gate_answer": gate_answer,
        "ready": bool(ready),
        "score": round(max(0.0, min(1.0, score)), 4),
        "sha256": sha,
        "status": status,
    })

present_count = sum(1 for row in rows if row["status"] == "REPORT_PRESENT")
ready_count = sum(1 for row in rows if row["ready"])
installed_count = sum(1 for row in rows if row["status"] != "MISSING_WRAPPER")

if present_count == 0:
    gate_answer = "NO_EVIDENCE_STACK_REPORTS_GENERATED_RESEARCH_ONLY"
elif ready_count == installed_count and installed_count >= 7:
    gate_answer = "STACK_PRESENT_BUT_OPERATIONAL_USE_STILL_LOCKED_RESEARCH_ONLY"
else:
    gate_answer = "EVIDENCE_STACK_GENERATED_CURRENT_GATES_STILL_BLOCK_PROMOTION_RESEARCH_ONLY"

payload: dict[str, Any] = {
    "schema": "qrds.evidence_stack_index.v1",
    "report_name": "qrds-evidence-stack-runner",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "symbols": symbols,
    "gate_answer": gate_answer,
    "gate_count": len(rows),
    "installed_gate_count": installed_count,
    "present_report_count": present_count,
    "ready_gate_count": ready_count,
    "policy_lock": "ACTIVE",
    "stack_items": rows,
    **SAFETY_FLAGS,
}
encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
payload["report_payload_sha256"] = hashlib.sha256(encoded).hexdigest()

stack_dir.mkdir(parents=True, exist_ok=True)
(stack_dir / "evidence_stack_index.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

md_lines = [
    "# QRDS Evidence Stack Runner v1",
    "",
    f"Gate answer: `{gate_answer}`",
    "",
    "| Gate | Status | Ready | Answer |",
    "|---|---:|---:|---|",
]
for row in rows:
    md_lines.append(f"| {row['gate_id']} {row['title']} | {row['status']} | {row['ready']} | `{row['gate_answer']}` |")
md_lines.extend([
    "",
    "## Safety flags",
    "",
    "This stack is `INTERACTIVE_RESEARCH_ONLY`. It cannot generate signals, orders, recommendations, allocation, portfolio decisions, position sizing, exchange connections, API-key usage, or real-capital actions.",
])
(stack_dir / "evidence_stack.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

css = """
body{font-family:Arial,sans-serif;margin:32px;line-height:1.45;background:#f7f7f7;color:#111}.card{background:#fff;border:1px solid #ddd;border-radius:12px;padding:18px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.05)}.badge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;background:#eee}.lock{background:#111;color:#fff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.metric{font-size:28px;font-weight:700}table{border-collapse:collapse;width:100%;background:#fff}th,td{border-bottom:1px solid #ddd;padding:9px;text-align:left;font-size:14px}th{background:#f0f0f0}a{color:#0645ad}.muted{color:#666}.answer{font-family:monospace;font-size:14px;word-break:break-word}
"""

def yesno(value: Any) -> str:
    return "YES" if value else "NO"

cards = "".join(
    f"<div class='card'><div class='badge'>{html.escape(row['gate_id'])}</div> "
    f"<h3>{html.escape(row['title'])}</h3>"
    f"<p class='answer'>{html.escape(row['gate_answer'])}</p>"
    f"<p>Status: <b>{html.escape(row['status'])}</b> • Ready: <b>{yesno(row['ready'])}</b> • Score: <b>{row['score']}</b></p>"
    f"<p><a href='{html.escape(row['html_path'])}'>Open gate screen</a></p></div>"
    for row in rows
)
flag_rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k, v in SAFETY_FLAGS.items())
report_rows = "".join(
    f"<tr><td>{html.escape(row['gate_id'])}</td><td>{html.escape(row['status'])}</td><td>{html.escape(str(row['ready']))}</td><td class='answer'>{html.escape(row['gate_answer'])}</td><td>{html.escape(row['sha256'][:16])}</td></tr>"
    for row in rows
)
html_text = f"""<!doctype html>
<html lang='en'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>QRDS Evidence Stack</title><style>{css}</style></head>
<body>
  <h1>QRDS/QOS • Gate BTC • Evidence Stack Runner</h1>
  <p class='muted'>Single-command research-only runner for 8L → 8R. This hub links the generated gate screens and records the final policy lock state.</p>
  <p><span class='badge lock'>Policy lock: ACTIVE</span> <span class='badge'>Mode: INTERACTIVE_RESEARCH_ONLY</span></p>
  <div class='card'><h2>Gate answer</h2><p class='answer'>{html.escape(gate_answer)}</p></div>
  <div class='grid'>
    <div class='card'><div class='metric'>{present_count}</div><div>Reports present</div></div>
    <div class='card'><div class='metric'>{ready_count}</div><div>Ready gates</div></div>
    <div class='card'><div class='metric'>{installed_count}</div><div>Installed gates</div></div>
    <div class='card'><div class='metric'>{len(symbols)}</div><div>Symbols</div></div>
  </div>
  <h2>Open generated screens</h2>
  <div class='grid'>{cards}</div>
  <h2>Stack table</h2>
  <table><thead><tr><th>Gate</th><th>Status</th><th>Ready</th><th>Answer</th><th>SHA256</th></tr></thead><tbody>{report_rows}</tbody></table>
  <h2>Safety flags</h2>
  <table><tbody>{flag_rows}</tbody></table>
  <p class='muted'>Generated at {html.escape(payload['generated_at'])} • SHA256 {html.escape(payload['report_payload_sha256'])}</p>
</body></html>"""
(stack_dir / "index.html").write_text(html_text, encoding="utf-8")

print(json.dumps({
    "schema": payload["schema"],
    "report_name": payload["report_name"],
    "gate_answer": payload["gate_answer"],
    "html_path": str(stack_dir / "index.html"),
    "index_path": str(stack_dir / "evidence_stack_index.json"),
    "present_report_count": present_count,
    "ready_gate_count": ready_count,
    "installed_gate_count": installed_count,
    "policy_lock": "ACTIVE",
    **SAFETY_FLAGS,
}, indent=2, sort_keys=True))
PYSTACK

cat <<EOF

[QRDS STACK] Evidence stack hub generated: $HUB_OUT/index.html
[QRDS STACK] Scope: research workflow only; no signal, no recommendation, no order.
EOF
