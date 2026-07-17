from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase391_accepts_only_manual_or_pull_request_workflow(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    workflow = tmp_path/".github/workflows/qrds-release-gate-windows-linux.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: x\non:\n  workflow_dispatch:\n  pull_request:\npermissions:\n  contents: read\n",encoding="utf-8")
    module = load_phase_module(391)
    p390 = write_json(tmp_path/"390.json",payload(390))
    result = module.build(p390,output_dir=project/"artifacts/phase391",project_root=project,git_root=tmp_path)
    assert result["workflow_configuration_valid"] is True
    assert result["push_trigger_present"] is False
    assert result["forbidden_workflow_tokens"] == []
    assert_locked(result)
