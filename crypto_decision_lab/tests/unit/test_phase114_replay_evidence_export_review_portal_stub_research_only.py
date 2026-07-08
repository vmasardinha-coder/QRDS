from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import build_audit_trail
from crypto_decision_lab.scripts.phase112_replay_evidence_export_review_notes_schema_research_only import build_review_notes_schema
from crypto_decision_lab.scripts.phase113_replay_evidence_export_review_scorecard_research_only import build_scorecard
from crypto_decision_lab.scripts.phase114_replay_evidence_export_review_portal_stub_research_only import (
    READY_GATE,
    build_phase114,
    build_portal_stub,
    render_portal,
)

def test_phase114_portal_stub_passes():
    portal = build_portal_stub()
    assert portal["gate"] == READY_GATE
    assert portal["portal_pass"] is True
    assert portal["portal_status"] == "PASS_RESEARCH_ONLY"
    assert portal["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert portal["operational_score_total"] == 0

def test_phase114_html_contains_boundaries():
    html = render_portal(build_audit_trail(), build_review_notes_schema(), build_scorecard())
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "Decision layer allowed: False" in html
    assert "trading_signal_generated: False" in html
    assert "allocation_generated: False" in html
    assert "canonical_data_writes: 0" in html
    assert "cannot validate edge" in html

def test_phase114_locks_are_closed():
    portal = build_portal_stub()
    assert portal["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert portal["edge_validated"] is False
    assert portal["decision_layer_allowed"] is False
    assert portal["safe_apply_allowed"] is False
    assert portal["promotion_allowed"] is False
    assert portal["canonical_data_writes"] == 0

def test_phase114_builds_artifacts(tmp_path):
    result = build_phase114(tmp_path / "phase114")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase114" / "phase114_replay_evidence_export_review_portal_stub.json").exists()
    assert (tmp_path / "phase114" / "phase114_replay_evidence_export_review_portal_stub.html").exists()
