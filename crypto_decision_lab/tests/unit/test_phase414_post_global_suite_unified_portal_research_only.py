from tests.unit._phase406_415_fixtures import assert_locked,build_chain

def test_phase414(tmp_path):
    project,results,_=build_chain(tmp_path,414)
    r=results[414]
    assert r["portal_ready"] is True and "BLOCKED_RESEARCH_ONLY" in (project/"artifacts"/"phase414_post_global_suite_unified_portal_research_only"/"index.html").read_text(encoding="utf-8")
    assert_locked(r)
