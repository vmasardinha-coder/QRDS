from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase352_requires_manual_governance(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 351)
    result = run_module(project, "phase352_new_question_governance_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase352_new_question_governance_research_only/phase352_new_question_governance.json").read_text())
    assert data["required_review_gate_count"] == 8
    assert data["new_family_opened"] is False
    assert data["new_hypotheses_registered"] == 0
