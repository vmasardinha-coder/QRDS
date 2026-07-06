from pathlib import Path
import json
from crypto_decision_lab.scripts.phase46_shadow_journal_schema_integrated_repo_hygiene import READY_GATE, build_phase46

def test_phase46_builds_shadow_journal_schema(tmp_path):
    result = build_phase46(tmp_path / "phase46")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 6
    assert result["schema_field_count"] >= 10
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["canonical_data_writes"] == 0
    schema = json.loads((out / "shadow_journal_schema.json").read_text())
    assert schema["shadow_decision_allowed"] is False
    assert schema["decision_layer_allowed"] is False
    assert schema["recommendation_generated"] is False
    for name in ["index.html", "schema.html", "manual_workflow.html", "repo_hygiene.html", "safety_lock.html", "shadow_journal_template.csv", "phase46_safety_status.json", "phase46_checksums.json"]:
        assert (out / name).exists(), name
