from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase350_seals_family_with_zero_budget(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 349)
    result = run_module(project, "phase350_abstention_closure_integrity_seal_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase350_abstention_closure_integrity_seal_research_only/phase350_abstention_closure_integrity_seal.json").read_text())
    assert data["closure_sealed"] is True
    assert data["closure_reopen_allowed"] is False
    assert data["active_experiment_budget"] == 0
