from crypto_decision_lab.scripts.phase182_gap_matrix_research_only import (
    READY_GATE,
    build_gap_matrix,
    build_phase182,
)

def test_phase182_gap_matrix_passes():
    matrix = build_gap_matrix()
    assert matrix["gate"] == READY_GATE
    assert matrix["gap_matrix_pass"] is True
    assert matrix["artifact_based_matrix"] is True
    assert matrix["row_count"] == 5
    assert matrix["invalid_row_count"] == 0

def test_phase182_rows_are_blocking():
    matrix = build_gap_matrix()
    assert all(row["gap_type"] == "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY" for row in matrix["rows"])
    assert all(row["required_before_promotion"] is True for row in matrix["rows"])
    assert all(row["currently_satisfied"] is False for row in matrix["rows"])
    assert all(row["blocks_promotion"] is True for row in matrix["rows"])
    assert all(row["operational_effect"] == "NONE_RESEARCH_ONLY" for row in matrix["rows"])

def test_phase182_forbidden_outputs_are_present():
    matrix = build_gap_matrix()
    forbidden = {row["forbidden_output"] for row in matrix["rows"]}
    assert forbidden == {
        "operational_decision_payload",
        "decision_layer_output",
        "shadow_decision_output",
        "safe_apply_payload",
        "canonical_write_payload",
    }

def test_phase182_locks_are_closed():
    matrix = build_gap_matrix()
    assert matrix["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert matrix["shadow_decision_allowed"] is False
    assert matrix["decision_layer_allowed"] is False
    assert matrix["promotion_allowed"] is False
    assert matrix["safe_apply_allowed"] is False
    assert matrix["canonical_data_writes"] == 0

def test_phase182_builds_artifact(tmp_path):
    result = build_phase182(tmp_path / "phase182")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase182" / "phase182_gap_matrix.json").exists()
