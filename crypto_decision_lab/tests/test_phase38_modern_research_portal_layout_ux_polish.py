from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module(project: Path):
    path = project / "scripts" / "phase38_modern_research_portal_layout_ux_polish.py"
    spec = importlib.util.spec_from_file_location("phase38_modern", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "QRDS"
    (root / "crypto_decision_lab" / "scripts").mkdir(parents=True)
    (root / "crypto_decision_lab" / "docs" / "reports").mkdir(parents=True)
    return root


def copy_generator_into(root: Path):
    current_project = Path(__file__).resolve().parents[1]
    src = current_project / "scripts" / "phase38_modern_research_portal_layout_ux_polish.py"
    dst = root / "crypto_decision_lab" / "scripts" / src.name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def seed_phase37(root: Path):
    phase37 = root / "artifacts" / "phase37_export_review_bundle_single_portal_index"
    phase37.mkdir(parents=True)
    (phase37 / "review_bundle.html").write_text("PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY", encoding="utf-8")
    (phase37 / "review_bundle_index.json").write_text(json.dumps({
        "gate": "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY",
        "phase36_pages_present": 11,
    }), encoding="utf-8")
    source = phase37 / "source_phase36_portal"
    source.mkdir()
    for name in [
        "index.html", "data_trust.html", "market_snapshot.html", "regime_map.html", "volatility_risk.html",
        "recent_history.html", "sparklines.html", "edge_ledger.html", "freshness_audit.html", "safety_lock.html", "exports_reports.html",
    ]:
        (source / name).write_text(f"<!doctype html><html><body>{name}</body></html>", encoding="utf-8")
    return phase37


def test_phase38_ready_generation(tmp_path: Path):
    root = make_root(tmp_path)
    copy_generator_into(root)
    seed_phase37(root)
    module = load_module(root / "crypto_decision_lab")
    result = module.run(root, None, None)
    out = root / "artifacts" / "phase38_modern_research_portal_layout_ux_polish"
    assert result["gate"] == "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_READY_RESEARCH_ONLY"
    assert result["modern_portal_ready"] is True
    assert result["modern_pages_present"] == 11
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (out / "index.html").exists()
    assert (out / "assets" / "qrds_modern.css").exists()
    assert (out / "modern_portal_navigation.json").exists()
    assert (out / "phase38_modern_research_portal_layout_ux_polish.zip").exists()


def test_phase38_missing_phase37_is_needs_review_not_crash(tmp_path: Path):
    root = make_root(tmp_path)
    copy_generator_into(root)
    module = load_module(root / "crypto_decision_lab")
    result = module.run(root, None, None)
    out = root / "artifacts" / "phase38_modern_research_portal_layout_ux_polish"
    assert result["gate"] == "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_NEEDS_REVIEW_RESEARCH_ONLY"
    assert result["modern_portal_ready"] is False
    assert result["modern_pages_present"] == 11
    assert (out / "index.html").exists()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["recommendation_generated"] is False
