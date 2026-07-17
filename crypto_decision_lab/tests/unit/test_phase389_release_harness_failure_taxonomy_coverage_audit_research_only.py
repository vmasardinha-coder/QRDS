from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase389_covers_frozen_failure_taxonomy(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(389)
    p383 = write_json(tmp_path/"383.json", payload(383))
    p388 = write_json(tmp_path/"388.json", payload(388))
    result = module.build(p383,p388,output_dir=project/"artifacts/phase389",project_root=project,git_root=tmp_path)
    assert result["release_harness_coverage_complete"] is True
    assert result["missing_taxonomy_coverage"] == []
    assert len(result["frozen_failure_taxonomy"]) >= 8
    assert_locked(result)
