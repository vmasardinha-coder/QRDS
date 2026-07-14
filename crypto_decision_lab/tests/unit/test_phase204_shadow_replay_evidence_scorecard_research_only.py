from pathlib import Path
import json
from crypto_decision_lab.scripts.phase204_shadow_replay_evidence_scorecard_research_only import build_phase204


def test_phase204_scores_evidence_without_promotion(tmp_path: Path) -> None:
    values = [
        {"phase": 200, "data_trust_checkpoint_ready": True, "findings": {}, "finding_total": 3, "locks": {"operational_status": "BLOCKED_RESEARCH_ONLY"}},
        {"phase": 202, "reproducible": True},
        {"phase": 203, "causality_audit_passed": True},
    ]
    paths = []
    for index, value in enumerate(values):
        path = tmp_path / f"p{index}.json"; path.write_text(json.dumps(value)); paths.append(path)
    result = build_phase204(*paths, tmp_path / "out")
    assert result["evidence_score"] == 100
    assert result["promotion_allowed"] is False
    assert result["predictive_validity_established"] is False
    assert result["valid_for_decision"] is False
