import json
import subprocess
import sys
from pathlib import Path

REQUIRED_PAGES = [
    "index.html",
    "data_trust.html",
    "market_snapshot.html",
    "regime_map.html",
    "volatility_risk.html",
    "recent_history.html",
    "sparklines.html",
    "edge_ledger.html",
    "freshness_audit.html",
    "safety_lock.html",
    "exports_reports.html",
]
REQUIRED_EXPORTS = [
    "unified_portal_manifest.csv",
    "unified_portal_navigation.json",
    "unified_portal_data.json",
    "unified_portal_exports_manifest.csv",
    "unified_portal_safety_status.json",
    "phase36_unified_risk_regime_research_portal_shell_pack.json",
    "phase36_unified_risk_regime_research_portal_shell_pack_index.json",
    "phase36_unified_risk_regime_research_portal_shell_pack.md",
]
SAFETY = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}


def script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "phase37_export_review_bundle_single_portal_index.py"


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "QRDS"
    (root / "crypto_decision_lab" / "docs" / "reports").mkdir(parents=True)
    (root / "crypto_decision_lab" / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md").write_text("# status\n", encoding="utf-8")
    return root


def make_phase36_portal(root: Path) -> Path:
    portal = root / "artifacts" / "phase36_unified_risk_regime_research_portal_shell_pack"
    portal.mkdir(parents=True)
    for name in REQUIRED_PAGES:
        portal.joinpath(name).write_text(f"<html>{name}</html>\n", encoding="utf-8")
    portal.joinpath("unified_portal_manifest.csv").write_text("name\nindex.html\n", encoding="utf-8")
    portal.joinpath("unified_portal_navigation.json").write_text(json.dumps({"pages": REQUIRED_PAGES}), encoding="utf-8")
    portal.joinpath("unified_portal_exports_manifest.csv").write_text("name\n", encoding="utf-8")
    portal.joinpath("unified_portal_data.json").write_text(json.dumps({"gate": "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY", **SAFETY}), encoding="utf-8")
    portal.joinpath("unified_portal_safety_status.json").write_text(json.dumps(SAFETY), encoding="utf-8")
    portal.joinpath("phase36_unified_risk_regime_research_portal_shell_pack.json").write_text(json.dumps({"gate": "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY", **SAFETY}), encoding="utf-8")
    portal.joinpath("phase36_unified_risk_regime_research_portal_shell_pack_index.json").write_text(json.dumps({"gate": "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY"}), encoding="utf-8")
    portal.joinpath("phase36_unified_risk_regime_research_portal_shell_pack.md").write_text("PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY\n", encoding="utf-8")
    return portal


def run_generator(root: Path, portal: Path | None, out: Path):
    cmd = [sys.executable, str(script_path()), "--root", str(root), "--output-dir", str(out)]
    if portal is not None:
        cmd.extend(["--portal-dir", str(portal)])
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_phase37_ready_bundle_from_valid_phase36_portal(tmp_path):
    root = make_root(tmp_path)
    portal = make_phase36_portal(root)
    out = root / "artifacts" / "phase37_export_review_bundle_single_portal_index"
    proc = run_generator(root, portal, out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((out / "review_bundle_index.json").read_text(encoding="utf-8"))
    assert data["gate"] == "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY"
    assert data["review_bundle_ready"] is True
    assert data["present_phase36_page_count"] == 11
    assert data["edge_validated"] is False
    assert data["shadow_decision_allowed"] is False
    assert data["decision_layer_allowed"] is False
    assert data["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert data["canonical_data_writes"] == 0
    assert (out / "index.html").exists()
    assert (out / "review_bundle.html").exists()
    assert (out / "review_bundle_manifest.csv").exists()
    assert (out / "review_bundle_checksums.json").exists()
    assert (out / "QRDS_PHASE37_EXPORT_REVIEW_BUNDLE_RESEARCH_ONLY.zip").exists()


def test_phase37_missing_input_is_needs_review_not_crash(tmp_path):
    root = make_root(tmp_path)
    missing_portal = root / "artifacts" / "missing_phase36"
    out = root / "artifacts" / "phase37_missing"
    proc = run_generator(root, missing_portal, out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads((out / "review_bundle_index.json").read_text(encoding="utf-8"))
    assert data["gate"] == "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_NEEDS_REVIEW_RESEARCH_ONLY"
    assert data["review_bundle_ready"] is False
    assert data["present_phase36_page_count"] == 0
    assert data["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert data["trading_signal_generated"] is False
    assert (out / "index.html").exists()
