from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import (
    READY_GATE,
    build_audit_trail,
    build_phase111,
    render_markdown,
)

def test_phase111_audit_trail_passes():
    audit = build_audit_trail()
    assert audit["gate"] == READY_GATE
    assert audit["audit_trail_pass"] is True
    assert audit["event_count"] == 5
    assert audit["failed_events"] == []
    assert audit["blocked_exports_preserved"] is True

def test_phase111_events_cover_106_to_110():
    audit = build_audit_trail()
    assert [event["phase"] for event in audit["events"]] == [106, 107, 108, 109, 110]
    assert all(event["status"] == "PASS_RESEARCH_ONLY" for event in audit["events"])

def test_phase111_locks_are_closed():
    audit = build_audit_trail()
    assert audit["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert audit["edge_validated"] is False
    assert audit["decision_layer_allowed"] is False
    assert audit["safe_apply_allowed"] is False
    assert audit["promotion_allowed"] is False
    assert audit["canonical_data_writes"] == 0
    assert audit["trading_signal_generated"] is False
    assert audit["allocation_generated"] is False

def test_phase111_markdown_contains_audit_boundary():
    md = render_markdown(build_audit_trail())
    assert READY_GATE in md
    assert "Blocked exports preserved: True" in md
    assert "canonical_data_writes: 0" in md

def test_phase111_builds_artifacts(tmp_path):
    result = build_phase111(tmp_path / "phase111")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase111" / "phase111_replay_evidence_export_audit_trail.json").exists()
    assert (tmp_path / "phase111" / "phase111_replay_evidence_export_audit_trail.md").exists()
