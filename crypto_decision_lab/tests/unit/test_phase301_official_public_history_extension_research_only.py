from pathlib import Path

from crypto_decision_lab.scripts import phase301_official_public_history_extension_research_only as phase301


def test_phase301_public_registry_and_fixture_preserve_research_locks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(phase301, "ROOT", tmp_path)
    payload = phase301.build_fixture(tmp_path / "artifacts/phase301", hours=800)

    assert payload["phase"] == 301
    assert payload["complete"] is True
    assert payload["substantially_longer_than_phase300_720h"] is True
    assert payload["forward_evidence_credit"] == 0
    assert payload["historical_backfill_to_forward_clock"] is False
    assert payload["locks"]["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert payload["locks"]["action_status"] == "NO_ACTION_RESEARCH_ONLY"
    assert payload["locks"]["capital_used"] == 0
    assert payload["locks"]["position_size"] == 0

    for endpoint in payload["official_endpoint_registry"].values():
        assert endpoint["auth_required"] is False
        assert endpoint["endpoint"].startswith("https://")
        assert endpoint["docs"].startswith("https://")

    for dataset in payload["datasets"].values():
        assert (tmp_path / dataset["path"]).is_file()
