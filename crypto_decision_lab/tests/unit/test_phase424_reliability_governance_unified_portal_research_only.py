from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase424(tmp_path):
    project, results, _ = build_chain(tmp_path, 424)
    result = results[424]
    assert result["portal_ready"] is True
    portal = project / "artifacts" / "phase424_reliability_governance_unified_portal_research_only" / "index.html"
    assert "BLOCKED_RESEARCH_ONLY" in portal.read_text(encoding="utf-8")
    assert_locked(result)
