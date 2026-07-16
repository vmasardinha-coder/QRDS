from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_project

def test_phase346_registers_negative_evidence(tmp_path):
    _, project = seed_project(tmp_path)
    result = run_module(project, "phase346_abstention_negative_evidence_registration_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase346_abstention_negative_evidence_registration_research_only/phase346_abstention_negative_evidence_registration.json").read_text())
    assert data["negative_evidence_registered"] is True
    assert data["eligible_template_count"] == 0
    assert data["locks"]["capital_used"] == 0
