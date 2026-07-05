#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
MOD="$SRC/crypto_decision_lab/reports/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.py"
OUT="$PROJECT/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"

if [ ! -f "$MOD" ]; then
  echo "[QRDS 30A HOTFIX] Missing Phase 30 module: $MOD"
  exit 1
fi

echo "[QRDS 30A HOTFIX] Patching dashboard readiness alias handling..."
cp "$MOD" "$MOD.bak_30A_aliases"

python - <<'PY'
from pathlib import Path
import re

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.py")
text = path.read_text(encoding="utf-8")

replacement = '''
def _ready_from_aliases(p: dict[str, Any], aliases: list[str]) -> tuple[bool, str]:
    # Robust aliases across previous phase index schemas.
    # Read-only compatibility fix; does not relax safety gates.
    for key in aliases:
        if bool(p.get(key, False)):
            return True, key
    payload = p.get("payload")
    if isinstance(payload, dict):
        for key in aliases:
            if bool(payload.get(key, False)):
                return True, f"payload.{key}"
    gate = str(p.get("gate_answer", ""))
    if "READY_RESEARCH_ONLY" in gate and "NEEDS_REVIEW" not in gate:
        return True, "gate_answer"
    return False, aliases[0] if aliases else "missing_ready_alias"


def _component_rows(phases: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    specs = [
        (
            "PHASE16_CONSENSUS",
            "multisource_consensus",
            "phase16",
            ["consensus_baseline_ready", "multisource_consensus_baseline_ready", "consensus_ready"],
            "Consensus multi-source",
        ),
        (
            "PHASE17_QUALITY_DRIFT",
            "quality_drift",
            "phase17",
            ["quality_drift_monitor_ready", "consensus_quality_drift_monitor_ready", "quality_monitor_ready"],
            "Quality/drift monitor",
        ),
        (
            "PHASE18_FEATURE_REGIME",
            "feature_regime",
            "phase18",
            ["feature_regime_diagnostics_ready", "research_feature_regime_diagnostics_ready", "feature_diagnostics_ready"],
            "Feature/regime diagnostics",
        ),
        (
            "PHASE19_OFFLINE_HARNESS",
            "offline_harness",
            "phase19",
            ["harness_ready", "offline_experiment_harness_ready", "experiment_harness_ready"],
            "Offline experiment harness",
        ),
        (
            "PHASE20_BASELINES",
            "baseline_null_models",
            "phase20",
            ["baseline_ready", "baseline_metrics_null_models_ready", "baseline_metrics_ready", "null_models_ready"],
            "Baseline/null model harness",
        ),
        (
            "PHASE25_STRENGTHENED_BASELINES",
            "strengthened_vol_baselines",
            "phase25",
            ["vol_feature_baseline_strengthening_ready", "volatility_feature_baseline_strengthening_ready"],
            "Strengthened volatility baselines",
        ),
        (
            "PHASE29_COMPRESSED_RETEST",
            "compressed_regime_retest",
            "phase29",
            ["compressed_regime_retest_ready", "compressed_edge_retest_ready"],
            "Compressed regime retest",
        ),
    ]
    for station, component_id, phase_key, aliases, label in specs:
        p = phases.get(phase_key, {})
        ready, resolved_key = _ready_from_aliases(p, aliases)
        rows.append({
            "station": station,
            "component_id": component_id,
            "label": label,
            "index_present": bool(p.get("_present")),
            "ready_key": resolved_key,
            "ready": ready,
            "gate_answer": p.get("gate_answer", "MISSING"),
            "source": SOURCE,
        })
    return rows


'''

text2 = re.sub(
    r'def _component_rows\(phases: dict\[str, dict\[str, Any\]\]\) -> list\[dict\[str, Any\]\]:.*?\n\ndef _evidence_rows',
    replacement + "\ndef _evidence_rows",
    text,
    flags=re.S,
)

if text2 == text:
    raise SystemExit("Patch failed: _component_rows block not found")

path.write_text(text2, encoding="utf-8")
PY

echo "[QRDS 30A HOTFIX] Adding focused regression test for readiness alias compatibility..."
cat > "$PROJECT/tests/regression/test_phase30_readiness_aliases_hotfix.py" <<'PY'
import json
from pathlib import Path

from crypto_decision_lab.reports.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack import build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack


def _write_index(root: Path, rel: str, payload: dict) -> None:
    p = root / "crypto_decision_lab" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")


def test_phase30_accepts_ready_aliases_without_unlocking_decisions(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_index(root, "artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json", {"gate_answer": "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_READY_RESEARCH_ONLY", "payload": {"consensus_baseline_ready": True}})
    _write_index(root, "artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json", {"gate_answer": "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY", "payload": {"quality_drift_monitor_ready": True}})
    _write_index(root, "artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json", {"gate_answer": "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY_RESEARCH_ONLY", "payload": {"feature_regime_diagnostics_ready": True}})
    _write_index(root, "artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json", {"gate_answer": "PHASE19_OFFLINE_EXPERIMENT_HARNESS_READY_RESEARCH_ONLY", "offline_experiment_harness_ready": True})
    _write_index(root, "artifacts/phase20_baseline_metrics_null_models_harness_pack/phase20_baseline_metrics_null_models_harness_pack_index.json", {"gate_answer": "PHASE20_BASELINE_METRICS_NULL_MODELS_READY_RESEARCH_ONLY", "baseline_metrics_null_models_ready": True})
    _write_index(root, "artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json", {"gate_answer": "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY_RESEARCH_ONLY", "vol_feature_baseline_strengthening_ready": True})
    _write_index(root, "artifacts/phase29_compressed_regime_edge_retest_pack/phase29_compressed_regime_edge_retest_pack_index.json", {"gate_answer": "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_READY_RESEARCH_ONLY", "compressed_regime_retest_ready": True, "stable_compressed_candidate_count": 0, "edge_operationally_validated": False, "decision_layer_allowed": False})

    result = build_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY"
    assert payload["risk_regime_dashboard_research_ready"] is True
    assert payload["edge_validated"] is False
    assert payload["shadow_decision_allowed"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
PY

echo "[QRDS 30A HOTFIX] Running targeted tests..."
cd "$PROJECT"
pytest -q \
  tests/unit/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.py \
  tests/integration/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_cli.py \
  tests/regression/test_phase30_missing_inputs_needs_review.py \
  tests/regression/test_phase30_readiness_aliases_hotfix.py

echo "[QRDS 30A HOTFIX] Running full test suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[QRDS 30A HOTFIX] Regenerating Phase 30 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path
p = Path("crypto_decision_lab/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))
for k in [
    "gate_answer","station","no_edge_checkpoint_ready","phase29_retest_ready","data_nature",
    "stable_compressed_candidate_count","edge_validated","edge_operationally_validated","risk_regime_dashboard_research_ready",
    "shadow_decision_allowed","decision_layer_allowed","next_research_path","operational_status","modeling_status",
    "safe_apply_allowed","promotion_allowed","canonical_data_writes","git_status_line_count","criteria_ready_count",
    "criteria_total_count","mean_checkpoint_score","policy_lock","app_mode",
]:
    print(f"{k}: {d.get(k)}")
print("[QRDS 30A HOTFIX] Component readiness:")
for r in d.get("payload", {}).get("component_readiness", []):
    print(f"{r['component_id']}: present={r['index_present']} ready={r['ready']} ready_key={r['ready_key']} gate={r['gate_answer']}")
PY

echo "[QRDS 30A HOTFIX] Committing changes..."
git add -A
git commit -m "Hotfix Phase 30 dashboard readiness aliases" || true
git push || true

echo "[QRDS 30A HOTFIX] Final status:"
git status --short
