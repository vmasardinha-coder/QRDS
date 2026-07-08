from pathlib import Path

from crypto_decision_lab.scripts.phase122_serve_root_fix_research_only import (
    READY_GATE,
    SERVE_SCRIPT_PATH,
    build_phase122,
    build_serve_root_fix,
)

def test_phase122_serve_root_fix_passes():
    fix = build_serve_root_fix()
    assert fix["gate"] == READY_GATE
    assert fix["serve_root_fix_pass"] is True
    assert fix["serve_script_path"] == SERVE_SCRIPT_PATH
    assert fix["local_index_url"] == "http://localhost:8765/index.html"

def test_phase122_script_points_to_index():
    fix = build_serve_root_fix()
    text = Path(fix["serve_script_path"]).read_text(encoding="utf-8")
    assert "http://localhost:$Port/index.html" in text
    assert "Serving index:" in text
    assert "python -m http.server" in text

def test_phase122_script_keeps_boundaries():
    fix = build_serve_root_fix()
    text = Path(fix["serve_script_path"]).read_text(encoding="utf-8")
    assert "Operational: BLOCKED_RESEARCH_ONLY" in text
    assert "Decision layer allowed: False" in text
    assert "trading_signal_generated: False" in text
    assert "allocation_generated: False" in text
    assert "canonical_data_writes: 0" in text

def test_phase122_locks_are_closed():
    fix = build_serve_root_fix()
    assert fix["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert fix["edge_validated"] is False
    assert fix["decision_layer_allowed"] is False
    assert fix["safe_apply_allowed"] is False
    assert fix["promotion_allowed"] is False
    assert fix["canonical_data_writes"] == 0

def test_phase122_builds_artifact(tmp_path):
    result = build_phase122(tmp_path / "phase122")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase122" / "phase122_serve_root_fix.json").exists()
