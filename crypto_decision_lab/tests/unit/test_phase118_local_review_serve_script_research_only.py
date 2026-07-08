from pathlib import Path

from crypto_decision_lab.scripts.phase118_local_review_serve_script_research_only import (
    READY_GATE,
    SERVE_SCRIPT_PATH,
    build_phase118,
    build_serve_script,
)

def test_phase118_serve_script_passes():
    serve = build_serve_script()
    assert serve["gate"] == READY_GATE
    assert serve["serve_script_pass"] is True
    assert serve["serve_script_path"] == SERVE_SCRIPT_PATH
    assert serve["portal_url"].startswith("http://localhost:8765/")

def test_phase118_script_contains_research_only_boundaries():
    serve = build_serve_script()
    text = Path(serve["serve_script_path"]).read_text(encoding="utf-8")
    assert "Operational: BLOCKED_RESEARCH_ONLY" in text
    assert "Decision layer allowed: False" in text
    assert "trading_signal_generated: False" in text
    assert "allocation_generated: False" in text
    assert "canonical_data_writes: 0" in text
    assert "python -m http.server" in text

def test_phase118_locks_are_closed():
    serve = build_serve_script()
    assert serve["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert serve["edge_validated"] is False
    assert serve["decision_layer_allowed"] is False
    assert serve["safe_apply_allowed"] is False
    assert serve["promotion_allowed"] is False
    assert serve["canonical_data_writes"] == 0
    assert serve["trading_signal_generated"] is False
    assert serve["allocation_generated"] is False

def test_phase118_builds_artifact(tmp_path):
    result = build_phase118(tmp_path / "phase118")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase118" / "phase118_local_review_serve_script.json").exists()
