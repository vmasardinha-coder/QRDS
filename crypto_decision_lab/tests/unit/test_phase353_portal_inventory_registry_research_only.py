from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase353_discovers_and_orders_existing_portals(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 352)
    result = run_module(project, "phase353_portal_inventory_registry_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase353_portal_inventory_registry_research_only/phase353_portal_inventory_registry.json").read_text())
    assert data["portal_count"] == 2
    assert data["latest_existing_portal"]["phase"] == 344
    assert (project / "docs/PORTAL_CATALOG.md").is_file()
