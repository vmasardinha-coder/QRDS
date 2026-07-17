from pathlib import Path
import pytest
from crypto_decision_lab.scripts.phase383_release_harness_and_repetitive_failure_scanner_research_only import build
from tests.unit._phase376_385_fixtures import base, write_json

def release_tree(root:Path):
    for idx in range(12):
        path=root/("src/crypto_decision_lab/scripts" if idx<6 else "tests/unit")/f"phase38{idx}_clean.py"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("VALUE = 1\n",encoding="utf-8")
    for rel in ("scripts/qrds_release_gate_376_385.ps1","scripts/serve_phase384_remediated_dataset_adoption_portal.ps1"):
        p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("Write-Host 'PASS'\n",encoding="utf-8")
    workflow=root/".github/workflows/qrds-release-gate-windows-linux.yml"; workflow.parent.mkdir(parents=True,exist_ok=True); workflow.write_text("name: test\n",encoding="utf-8")

def test_phase383_scans_release_and_passes(tmp_path:Path):
    release_tree(tmp_path); p382=write_json(tmp_path/"382.json",base(382,coexistence_pass=True)); ps=write_json(tmp_path/"ps.json",{"passed":True,"error_count":0}); installer=tmp_path/"installer.ps1"; installer.write_text("Write-Host 'clean'\n",encoding="utf-8"); r=build(p382,ps,tmp_path/"out",installer_path=installer,project_root=tmp_path); assert r["release_harness_pass"]

def test_phase383_blocks_observed_bad_pattern(tmp_path:Path):
    release_tree(tmp_path); bad=tmp_path/"src/crypto_decision_lab/scripts/phase380_bad.py"; bad.write_text('x = "pattern.sub(replacement"\n',encoding="utf-8"); p382=write_json(tmp_path/"382.json",base(382,coexistence_pass=True)); ps=write_json(tmp_path/"ps.json",{"passed":True,"error_count":0})
    with pytest.raises(RuntimeError,match="observed_pattern_findings_zero"): build(p382,ps,tmp_path/"out",project_root=tmp_path)



def test_phase383_actual_release_gate_is_windows_powershell_51_safe():
    from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ROOT
    text = (ROOT / "scripts/qrds_release_gate_376_385.ps1").read_text(encoding="utf-8-sig")
    assert "[System.Management.Automation.Language.Token[]]$tokens" in text
    assert "[System.Management.Automation.Language.ParseError[]]$parseErrors" in text
    assert "System.Collections.Generic.List[object]" not in text
    assert "$tokens = $null" not in text
    assert "errors = [object[]]$errors" in text


def test_phase383_actual_windows_workflow_uses_typed_parser_refs():
    from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import GIT_ROOT
    text = (GIT_ROOT / ".github/workflows/qrds-release-gate-windows-linux.yml").read_text(encoding="utf-8-sig")
    assert "[System.Management.Automation.Language.Token[]]$tokens" in text
    assert "[System.Management.Automation.Language.ParseError[]]$parseErrors" in text
    assert "$tokens=$null; $parseErrors=$null" not in text
