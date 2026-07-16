from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase348_documents_failure_causes_without_rescue(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 346)
    result = run_module(project, "phase348_abstention_failure_cause_audit_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase348_abstention_failure_cause_audit_research_only/phase348_abstention_failure_cause_audit.json").read_text())
    assert data["failure_category_count"] >= 4
    assert data["parameter_rescue_recommended"] is False
    assert data["scientific_classification"] == "NEGATIVE_RESULT_NOT_SOFTWARE_FAILURE"
