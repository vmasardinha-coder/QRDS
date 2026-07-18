from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase399_audits_manual_pr_least_privilege_workflow(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    workflow=tmp_path/".github/workflows/qrds-release-gate-windows-linux.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: gate\non:\n  workflow_dispatch:\n  pull_request:\npermissions:\n  contents: read\n",encoding="utf-8")
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),399)
    p398=write_json(tmp_path/"398.json",payload(398))
    result=module.build(p398,output_dir=project/"artifacts/phase399",project_root=project,git_root=tmp_path)
    assert result["workflow_audit_pass"] is True
    assert result["push_trigger_present"] is False
    assert result["least_privilege_pass"] is True
    assert_locked(result)
