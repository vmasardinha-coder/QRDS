from pathlib import Path

from crypto_decision_lab.scripts.phase124_one_command_review_portal_runner_research_only import (
    READY_GATE,
    RUNNER_SCRIPT_PATH,
    SERVE_SCRIPT_PATH,
    build_phase124,
    build_runner,
)

def test_phase124_runner_passes():
    runner = build_runner()
    assert runner["gate"] == READY_GATE
    assert runner["runner_pass"] is True
    assert runner["runner_script_path"] == RUNNER_SCRIPT_PATH
    assert runner["serve_script_path"] == SERVE_SCRIPT_PATH
    assert runner["local_index_url"] == "http://localhost:8765/index.html"

def test_phase124_runner_script_exists_and_calls_serve_script():
    runner = build_runner()
    text = Path(runner["runner_script_path"]).read_text(encoding="utf-8")
    assert "serve_review_portal_research_only.ps1" in text
    assert "http://localhost:$Port/index.html" in text
    assert "& $serveScript -Port $Port" in text

def test_phase124_runner_keeps_boundaries():
    runner = build_runner()
    text = Path(runner["runner_script_path"]).read_text(encoding="utf-8")
    assert "Research-only mode" in text
    assert "Operational: BLOCKED_RESEARCH_ONLY" in text
    assert "Decision layer allowed: False" in text
    assert "trading_signal_generated: False" in text
    assert "allocation_generated: False" in text
    assert "canonical_data_writes: 0" in text

def test_phase124_locks_are_closed():
    runner = build_runner()
    assert runner["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert runner["edge_validated"] is False
    assert runner["decision_layer_allowed"] is False
    assert runner["safe_apply_allowed"] is False
    assert runner["promotion_allowed"] is False
    assert runner["canonical_data_writes"] == 0
    assert runner["trading_signal_generated"] is False
    assert runner["allocation_generated"] is False

def test_phase124_builds_artifact(tmp_path):
    result = build_phase124(tmp_path / "phase124")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase124" / "phase124_one_command_review_portal_runner.json").exists()
