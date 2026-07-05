from pathlib import Path
from crypto_decision_lab.reports.phase35_recent_history_sparkline_panels_pack import build_phase35_recent_history_sparkline_panels_pack

def test_phase35_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase35_recent_history_sparkline_panels_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["recent_history_sparkline_panels_ready"] is False
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
