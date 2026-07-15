from pathlib import Path

from crypto_decision_lab.scripts import phase303_finite_hypothesis_registry_v2_research_only as phase303
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import base_payload, write_json


def test_phase303_closes_exactly_twenty_four_hypotheses(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(phase303, "ROOT", tmp_path)
    source = base_payload(302, "TEST")
    source.update({"artifact_fingerprint": "a" * 64})
    source_path = tmp_path / "artifacts/phase302/phase302.json"
    write_json(source_path, source)

    payload = phase303.build(source_path, tmp_path / "artifacts/phase303")

    assert payload["phase"] == 303
    assert payload["experiment_budget"] == 24
    assert payload["registered_hypotheses"] == 24
    assert len(payload["hypotheses"]) == 24
    assert payload["registry_closed"] is True
    assert payload["budget_exhaustion_policy"] == "STOP_NO_EXTENSION"
    assert payload["post_result_parameter_changes_allowed"] is False
    assert payload["multiple_testing"]["method"] == "HOLM_BONFERRONI"
    assert payload["strategy_approved"] is False
    assert len({item["hypothesis_id"] for item in payload["hypotheses"]}) == 24
