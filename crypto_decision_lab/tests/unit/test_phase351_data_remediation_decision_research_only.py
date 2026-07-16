from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase351_allows_diagnostics_without_reopening_family(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 350)
    result = run_module(project, "phase351_data_remediation_decision_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase351_data_remediation_decision_research_only/phase351_data_remediation_decision.json").read_text())
    assert data["data_remediation_reopens_family"] is False
    assert data["data_remediation_authorizes_new_hypotheses"] is False
    assert data["public_network_collection_started"] is False
