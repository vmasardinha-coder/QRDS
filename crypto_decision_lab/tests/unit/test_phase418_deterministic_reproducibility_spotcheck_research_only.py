from tests.unit._phase416_425_fixtures import assert_locked, build_chain

def test_phase418(tmp_path):
    project, results, _ = build_chain(tmp_path, 418)
    result = results[418]
    assert result["reproducibility_spotcheck_pass"] is True
    assert result["spotcheck_hash_a"] == result["spotcheck_hash_b"]
    assert_locked(result)
