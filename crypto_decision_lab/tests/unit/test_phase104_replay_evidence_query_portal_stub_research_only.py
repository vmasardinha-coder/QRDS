from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import build_query_index
from crypto_decision_lab.scripts.phase102_replay_evidence_query_manifest_research_only import build_query_manifest
from crypto_decision_lab.scripts.phase103_replay_evidence_query_cli_dry_run_research_only import build_cli_dry_run
from crypto_decision_lab.scripts.phase104_replay_evidence_query_portal_stub_research_only import (
    READY_GATE,
    build_phase104,
    build_portal_stub,
    render_portal,
)

def test_phase104_portal_stub_passes():
    portal = build_portal_stub()
    assert portal["gate"] == READY_GATE
    assert portal["portal_pass"] is True
    assert portal["portal_status"] == "PASS_RESEARCH_ONLY"
    assert portal["blocked_query_count"] == 3

def test_phase104_html_contains_boundaries():
    html = render_portal(build_query_index(), build_query_manifest(), build_cli_dry_run())
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "Decision layer allowed: False" in html
    assert "cannot generate trading signals" in html
    assert "canonical_data_writes: 0" in html

def test_phase104_locks_are_closed():
    portal = build_portal_stub()
    assert portal["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert portal["edge_validated"] is False
    assert portal["decision_layer_allowed"] is False
    assert portal["safe_apply_allowed"] is False
    assert portal["promotion_allowed"] is False
    assert portal["canonical_data_writes"] == 0
    assert portal["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase104_builds_artifacts(tmp_path):
    result = build_phase104(tmp_path / "phase104")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase104" / "phase104_replay_evidence_query_portal_stub.json").exists()
    assert (tmp_path / "phase104" / "phase104_replay_evidence_query_portal_stub.html").exists()
