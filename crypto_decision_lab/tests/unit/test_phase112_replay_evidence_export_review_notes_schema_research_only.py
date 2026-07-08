from crypto_decision_lab.scripts.phase112_replay_evidence_export_review_notes_schema_research_only import (
    FORBIDDEN_EFFECTS,
    READY_GATE,
    REVIEW_SCHEMA,
    build_phase112,
    build_review_notes_schema,
)

def test_phase112_schema_passes():
    schema = build_review_notes_schema()
    assert schema["gate"] == READY_GATE
    assert schema["schema_pass"] is True
    assert schema["source_audit_pass"] is True
    assert schema["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert schema["human_review_required"] is True

def test_phase112_schema_has_no_approval_effect():
    schema = build_review_notes_schema()
    assert schema["review_schema"]["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert "edge_validation" in FORBIDDEN_EFFECTS
    assert "trading_signal" in FORBIDDEN_EFFECTS
    assert "allocation" in FORBIDDEN_EFFECTS
    assert "promotion" in FORBIDDEN_EFFECTS
    assert "canonical_write" in FORBIDDEN_EFFECTS
    assert len(FORBIDDEN_EFFECTS) == 9

def test_phase112_review_schema_fields_exist():
    assert REVIEW_SCHEMA["review_id"] == "string"
    assert REVIEW_SCHEMA["created_at_utc"] == "datetime_iso8601"
    assert "needs_review" in REVIEW_SCHEMA["finding_type"]
    assert "blocking_research_only" in REVIEW_SCHEMA["severity"]

def test_phase112_locks_are_closed():
    schema = build_review_notes_schema()
    assert schema["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert schema["edge_validated"] is False
    assert schema["decision_layer_allowed"] is False
    assert schema["safe_apply_allowed"] is False
    assert schema["promotion_allowed"] is False
    assert schema["canonical_data_writes"] == 0
    assert schema["trading_signal_generated"] is False
    assert schema["allocation_generated"] is False

def test_phase112_builds_artifact(tmp_path):
    result = build_phase112(tmp_path / "phase112")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase112" / "phase112_replay_evidence_export_review_notes_schema.json").exists()
