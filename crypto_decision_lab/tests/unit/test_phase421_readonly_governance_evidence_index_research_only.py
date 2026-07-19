from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase421(tmp_path):
    project, results, _ = build_chain(tmp_path, 421)
    result = results[421]
    assert result["governance_evidence_index_ready"] is True
    assert result["governance_evidence_index"]["mode"] == "READ_ONLY"
    assert_locked(result)
