from pathlib import Path
import json
from crypto_decision_lab.scripts.phase199_source_reconciliation_provenance_score_research_only import build_phase199


def test_phase199_scores_and_reconciles(tmp_path: Path) -> None:
    registry = {"phase": 196, "sources": [{"source_id": "src_1234567890abcdef", "relative_or_absolute_path": "data/a.csv", "content_sha256": "a" * 64, "source_role": "RESEARCH_INPUT", "read_only_evidence": True, "tracked_by_git": True}]}
    temporal = {"phase": 197, "source_audits": [{"source_id": "src_1234567890abcdef", "temporal_candidate": True, "inspection_status": "INSPECTED", "timezone_status": "UTC_OR_OFFSET_EXPLICIT", "invalid_timestamp_count": 0, "non_monotonic_timestamp_count": 0}]}
    anomaly = {"phase": 198, "source_audits": [{"source_id": "src_1234567890abcdef", "anomaly_flags": []}]}
    paths = []
    for name, value in (("r", registry), ("t", temporal), ("a", anomaly)):
        path = tmp_path / f"{name}.json"; path.write_text(json.dumps(value)); paths.append(path)
    payload = build_phase199(*paths, tmp_path / "out")
    assert payload["sources_reconciled"] is True
    assert payload["source_scores"][0]["provenance_score"] == 100
    assert payload["data_trust_validated"] is False
    assert payload["locks"]["decision_layer_allowed"] is False
