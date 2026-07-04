#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase16_multisource_consensus_baseline_pack"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

cd "$ROOT"

echo "[HOTFIX 16A] Patching Phase 16 missing-source summary schema..."

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase16_multisource_consensus_baseline_pack.py")
if not path.exists():
    raise SystemExit(f"Missing Phase 16 file: {path}")

text = path.read_text(encoding="utf-8")

old = '''    if not source_points or any(not pts for pts in source_points.values()):
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_source_points",
            "source_rows": {s: len(p) for s, p in source_points.items()},
        }
'''

new = '''    if not source_points or any(not pts for pts in source_points.values()):
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_source_points",
            "source_rows": {s: len(p) for s, p in source_points.items()},
            "consensus_rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "source_count": len(ready_sources),
            "ready_sources": ready_sources,
            "dispersion_bps_mean": 0.0,
            "dispersion_bps_median": 0.0,
            "dispersion_bps_p95": 0.0,
            "dispersion_bps_max": 0.0,
            "consensus_ann_vol_research": 0.0,
            "positive_return_rate_research": 0.0,
        }
'''

if old not in text:
    if '"consensus_rows": 0' in text and '"missing_source_points"' in text:
        print("[HOTFIX 16A] Missing-source schema already patched.")
    else:
        raise SystemExit("Could not locate missing-source summary block.")
else:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("[HOTFIX 16A] Missing-source summary schema patched.")
PY

cat > "$PROJECT/tests/regression/test_phase16_missing_source_summary_schema.py" <<'PY'
from pathlib import Path

from crypto_decision_lab.reports.phase16_multisource_consensus_baseline_pack import build_phase16_multisource_consensus_baseline_pack


def test_phase16_missing_source_summary_schema_does_not_crash(tmp_path: Path) -> None:
    result = build_phase16_multisource_consensus_baseline_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["consensus_baseline_ready"] is False
    assert payload["consensus_rows_total"] == 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False

    for summary in payload["coin_summaries"]:
        assert summary["consensus_rows"] == 0
        assert summary["first_timestamp"] == "MISSING"
        assert summary["last_timestamp"] == "MISSING"
        assert summary["reason"] == "missing_source_points"
PY

echo "[HOTFIX 16A] Running targeted Phase 16 tests..."
cd "$PROJECT"
pytest -q \
  tests/regression/test_phase16_missing_source_summary_schema.py \
  tests/unit/test_phase16_multisource_consensus_baseline_pack.py \
  tests/integration/test_phase16_multisource_consensus_baseline_pack_cli.py

echo "[HOTFIX 16A] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 16A] Generating Phase 16 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase16_multisource_consensus_baseline_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path
p = Path("crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 16A] Phase 16 summary:")
for k in [
    "gate_answer",
    "station",
    "consensus_baseline_ready",
    "data_nature",
    "ready_sources",
    "ready_source_count",
    "excluded_pending_sources",
    "coins",
    "coins_count",
    "min_consensus_rows_per_coin",
    "consensus_rows_total",
    "max_dispersion_mean_bps",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_consensus_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")
print("[HOTFIX 16A] Coin summaries:")
for s in d.get("payload", {}).get("coin_summaries", []):
    print(f"{s['coin']}: rows={s['consensus_rows']} first={s['first_timestamp']} last={s['last_timestamp']} sources={s['source_count']} dispersion_mean_bps={s['dispersion_bps_mean']} dispersion_p95_bps={s['dispersion_bps_p95']} ann_vol={s['consensus_ann_vol_research']} ready={s['ready']}")
print("[HOTFIX 16A] Consensus outputs:")
for o in d.get("payload", {}).get("consensus_outputs", []):
    print(f"{o['coin']}: rows={o['rows']} canonical_write={o['canonical_write']} path={o['path']}")
PY

echo "[HOTFIX 16A] Archiving root installers if present..."
cd "$ROOT"
mkdir -p scripts/archive/installers
for f in \
  "qrds_hotfix_16A_consensus_missing_source_schema.sh" \
  "qrds_hotfix_16A_consensus_missing_source_schema (1).sh" \
  "qrds_sprint_16A_to_16R_multisource_consensus_baseline_pack.sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[HOTFIX 16A] Archived $f"
  fi
done

echo "[HOTFIX 16A] Committing changes..."
git add -A
git commit -m "Fix Phase 16 missing-source consensus schema" || true
git push || true

echo "[HOTFIX 16A] Final status:"
git status --short
