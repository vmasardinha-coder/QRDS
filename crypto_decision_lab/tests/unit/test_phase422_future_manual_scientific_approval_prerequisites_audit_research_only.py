from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase422(tmp_path):
    project, results, _ = build_chain(tmp_path, 422)
    result = results[422]
    assert result["approval_prerequisites_audited"] is True
    assert result["approval_prerequisites_satisfied"] is False
    assert result["approval_granted"] is False
    assert_locked(result)
