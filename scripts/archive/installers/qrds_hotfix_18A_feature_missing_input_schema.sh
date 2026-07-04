#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase18_research_feature_regime_diagnostics_pack"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

cd "$ROOT"

echo "[HOTFIX 18A] Patching Phase 18 missing-input feature summary schema..."

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase18_research_feature_regime_diagnostics_pack.py")
if not path.exists():
    raise SystemExit(f"Missing Phase 18 file: {path}")

text = path.read_text(encoding="utf-8")

old = '''    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_consensus_rows",
            "rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "feature_rows": 0,
            "volatility_regime_counts": {},
            "dispersion_regime_counts": {},
            "momentum_regime_counts": {},
        }
'''

new = '''    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_consensus_rows",
            "rows": 0,
            "feature_rows": 0,
            "mature_feature_rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "rolling_vol_24h_ann_mean": 0.0,
            "rolling_vol_24h_ann_p95": 0.0,
            "rolling_vol_168h_ann_mean": 0.0,
            "rolling_vol_168h_ann_p95": 0.0,
            "dispersion_24h_mean": 0.0,
            "dispersion_24h_p95": 0.0,
            "max_drawdown_research": 0.0,
            "volatility_regime_counts": {},
            "dispersion_regime_counts": {},
            "momentum_regime_counts": {},
            "feature_maturity_counts": {},
            "vol24_quantiles": {"p33": 0.0, "p66": 0.0},
            "vol168_quantiles": {"p33": 0.0, "p66": 0.0},
            "dispersion_quantiles": {"p33": 0.0, "p66": 0.0},
        }
'''

if old not in text:
    if '"mature_feature_rows": 0' in text and '"missing_consensus_rows"' in text:
        print("[HOTFIX 18A] Missing-input schema already patched.")
    else:
        raise SystemExit("Could not locate missing-consensus summary block.")
else:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("[HOTFIX 18A] Missing-input summary schema patched.")
PY

cat > "$PROJECT/tests/regression/test_phase18_missing_input_summary_schema.py" <<'PY'
from pathlib import Path

from crypto_decision_lab.reports.phase18_research_feature_regime_diagnostics_pack import build_phase18_research_feature_regime_diagnostics_pack


def test_phase18_missing_input_summary_schema_is_complete(tmp_path: Path) -> None:
    result = build_phase18_research_feature_regime_diagnostics_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["feature_regime_diagnostics_ready"] is False
    assert payload["feature_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False

    for summary in payload["coin_feature_summaries"]:
        assert summary["reason"] == "missing_consensus_rows"
        assert summary["feature_rows"] == 0
        assert summary["mature_feature_rows"] == 0
        assert summary["rolling_vol_24h_ann_mean"] == 0.0
        assert summary["rolling_vol_24h_ann_p95"] == 0.0
        assert summary["dispersion_24h_p95"] == 0.0
        assert summary["max_drawdown_research"] == 0.0
        assert Path(result["html_path"]).exists()
PY

echo "[HOTFIX 18A] Running targeted Phase 18 tests..."
cd "$PROJECT"
pytest -q \
  tests/regression/test_phase18_missing_input_summary_schema.py \
  tests/unit/test_phase18_research_feature_regime_diagnostics_pack.py \
  tests/integration/test_phase18_research_feature_regime_diagnostics_pack_cli.py \
  tests/regression/test_phase18_missing_inputs_needs_review.py

echo "[HOTFIX 18A] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 18A] Generating Phase 18 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase18_research_feature_regime_diagnostics_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json")
if not p.exists():
    raise SystemExit("Phase 18 index was not generated.")

d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 18A] Phase 18 summary:")
for k in [
    "gate_answer",
    "station",
    "feature_regime_diagnostics_ready",
    "data_nature",
    "phase17_quality_drift_monitor_ready",
    "coins",
    "coins_count",
    "feature_rows_total",
    "min_feature_rows_per_coin",
    "min_mature_feature_rows_per_coin",
    "diagnostic_labels_are_signals",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_feature_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")
print("[HOTFIX 18A] Coin feature summaries:")
for s in d.get("payload", {}).get("coin_feature_summaries", []):
    print(f"{s['coin']}: rows={s['feature_rows']} mature={s['mature_feature_rows']} vol24_mean={s['rolling_vol_24h_ann_mean']} vol24_p95={s['rolling_vol_24h_ann_p95']} disp24_p95={s['dispersion_24h_p95']} max_dd={s['max_drawdown_research']} ready={s['ready']}")
print("[HOTFIX 18A] Feature outputs:")
for o in d.get("payload", {}).get("feature_outputs", []):
    print(f"{o['coin']}: rows={o['rows']} canonical_write={o['canonical_write']} path={o['path']}")
PY

echo "[HOTFIX 18A] Updating project status doc..."
python - <<'PY'
import json
from pathlib import Path

root = Path(".")
idx = root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json"
d = json.loads(idx.read_text(encoding="utf-8"))

status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
status_path.parent.mkdir(parents=True, exist_ok=True)
existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"

marker = "\n## Latest Phase 18 update\n"
before = existing.split(marker)[0].rstrip()
section = [
    marker.strip(),
    "",
    f"Updated at: {d.get('generated_at')}",
    "",
    f"- Phase 18 gate: `{d.get('gate_answer')}`",
    f"- Feature/regime diagnostics ready: `{d.get('feature_regime_diagnostics_ready')}`",
    f"- Feature rows total: `{d.get('feature_rows_total')}`",
    f"- Min feature rows per coin: `{d.get('min_feature_rows_per_coin')}`",
    f"- Min mature feature rows per coin: `{d.get('min_mature_feature_rows_per_coin')}`",
    f"- Diagnostic labels are signals: `{d.get('diagnostic_labels_are_signals')}`",
    f"- Operational status: `{d.get('operational_status')}`",
    f"- Canonical writes: `{d.get('canonical_data_writes')}`",
    "",
    "Diagnostic labels are research-only descriptors, not trading signals, recommendations, allocations, or operational decisions.",
    "",
]
status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")
print(f"[HOTFIX 18A] Updated {status_path}")
PY

echo "[HOTFIX 18A] Archiving root installers if present..."
cd "$ROOT"
mkdir -p scripts/archive/installers
for f in \
  "qrds_hotfix_18A_feature_missing_input_schema.sh" \
  "qrds_hotfix_18A_feature_missing_input_schema (1).sh" \
  "qrds_sprint_18A_to_18R_research_feature_regime_diagnostics_pack.sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[HOTFIX 18A] Archived $f"
  fi
done

echo "[HOTFIX 18A] Committing changes..."
git add -A
git commit -m "Fix Phase 18 missing input feature schema" || true
git push || true

echo "[HOTFIX 18A] Final status:"
git status --short
