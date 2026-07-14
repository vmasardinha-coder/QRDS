from pathlib import Path
import json
from crypto_decision_lab.scripts.phase200_data_trust_batch_checkpoint_research_only import build_phase200


def test_phase200_preserves_findings_and_locks(tmp_path: Path) -> None:
    payloads = [
        {"phase": 196, "registry_ready": True},
        {"phase": 197, "temporal_policy_ready": True, "summary": {"timezone_review_count": 1}},
        {"phase": 198, "anomaly_audit_ready": True, "summary": {"flagged_source_count": 1, "ohlc_invariant_violation_count": 2, "missing_value_count": 1}},
        {"phase": 199, "sources_reconciled": True, "provenance_scored": True, "summary": {}},
    ]
    paths = []
    for index, value in enumerate(payloads):
        path = tmp_path / f"p{index}.json"; path.write_text(json.dumps(value)); paths.append(path)
    result = build_phase200(*paths, tmp_path / "out")
    assert result["checkpoint_status"] == "READY_WITH_FINDINGS_RESEARCH_ONLY"
    assert result["finding_total"] == 5
    assert result["data_trust_validated"] is False
    assert result["valid_for_decision"] is False
