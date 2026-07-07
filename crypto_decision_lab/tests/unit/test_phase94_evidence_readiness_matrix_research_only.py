from crypto_decision_lab.scripts.phase94_evidence_readiness_matrix_research_only import (
    MATRIX,
    READY_GATE,
    build_matrix,
    build_phase94,
    render_markdown,
)

def test_phase94_matrix_is_research_only():
    matrix = build_matrix()
    assert matrix["gate"] == READY_GATE
    assert matrix["readiness_for_operations"] == "BLOCKED_RESEARCH_ONLY"
    assert matrix["promotion_score"] == 0
    assert matrix["promotion_effect"] == "NONE_RESEARCH_ONLY"

def test_phase94_all_promotion_weights_zero():
    matrix = build_matrix()
    assert len(matrix["matrix"]) == len(MATRIX)
    assert all(item["promotion_weight"] == 0 for item in matrix["matrix"])

def test_phase94_locks_are_closed():
    matrix = build_matrix()
    assert matrix["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert matrix["edge_validated"] is False
    assert matrix["decision_layer_allowed"] is False
    assert matrix["safe_apply_allowed"] is False
    assert matrix["promotion_allowed"] is False
    assert matrix["canonical_data_writes"] == 0

def test_phase94_markdown_contains_blocked_readiness():
    md = render_markdown(build_matrix())
    assert READY_GATE in md
    assert "Readiness for operations: BLOCKED_RESEARCH_ONLY" in md
    assert "Promotion score: 0" in md
    assert "cannot promote" in md

def test_phase94_builds_artifacts(tmp_path):
    result = build_phase94(tmp_path / "phase94")
    assert result["ready"] is True
    assert (tmp_path / "phase94" / "phase94_evidence_readiness_matrix.json").exists()
    assert (tmp_path / "phase94" / "phase94_evidence_readiness_matrix.md").exists()
