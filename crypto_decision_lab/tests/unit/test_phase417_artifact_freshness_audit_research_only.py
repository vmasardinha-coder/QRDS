from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase417(tmp_path):
    project, results, _ = build_chain(tmp_path, 417)
    result = results[417]
    assert result["freshness_audit_pass"] is True
    assert result["evidence_mutated"] is False
    assert_locked(result)
