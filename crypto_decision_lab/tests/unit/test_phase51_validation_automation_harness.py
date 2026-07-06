from crypto_decision_lab.scripts.phase51_validation_automation_harness import (
    READY_GATE,
    validate_phase_log,
    write_validation_summary,
)

def test_phase51_log_validation_accepts_safe_log():
    text = """
PHASE51_VALIDATION_AUTOMATION_HARNESS_READY_RESEARCH_ONLY
Operational: BLOCKED_RESEARCH_ONLY
Edge: False
canonical_data_writes: 0
Focused tests: PASS
Full suite: PASS
"""
    result = validate_phase_log(text, expected_gate=READY_GATE)
    assert result["ready"] is True
    assert result["gate_ok"] is True
    assert result["required_missing"] == []
    assert result["forbidden_found"] == []
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0

def test_phase51_log_validation_rejects_unsafe_log():
    text = """
PHASE51_VALIDATION_AUTOMATION_HARNESS_READY_RESEARCH_ONLY
Operational: ACTIVE
Edge: True
canonical_data_writes: 1
Focused tests: PASS
Full suite: PASS
"""
    result = validate_phase_log(text, expected_gate=READY_GATE)
    assert result["ready"] is False
    assert "Operational: ACTIVE" in result["forbidden_found"]
    assert "Edge: True" in result["forbidden_found"]

def test_phase51_summary_written(tmp_path):
    result = write_validation_summary(tmp_path, phase=51)
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase51_validation_automation_summary.json").exists()
    assert (tmp_path / "phase51_validation_automation_summary.md").exists()
