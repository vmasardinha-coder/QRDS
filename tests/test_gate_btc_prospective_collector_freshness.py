import json
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_factory.prospective_collector_freshness import classify, evaluate


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_classification_boundaries():
    assert classify(60, 60) == "FRESH"
    assert classify(91, 60) == "STALE_WARNING"
    assert classify(121, 60) == "HARD_STALE"
    assert classify(360, 240) == "FRESH"
    assert classify(361, 240) == "STALE_WARNING"
    assert classify(481, 240) == "HARD_STALE"


def test_evaluate_read_only_status(tmp_path: Path):
    xagent = tmp_path / "xagent.json"
    xmm = tmp_path / "xmm.json"
    xvol = tmp_path / "xvol.json"
    write(xagent, {"family_id": "F-XAGENT-DISAGREE", "generated_at_utc": "2026-09-23T15:38:00Z"})
    write(xmm, {"family_id": "F-XMM-INVENTORY", "latest_observed_at_utc": "2026-09-23T13:41:00Z"})
    write(xvol, {"family_id": "F-XVOL-SURFACE", "latest_observed_at_utc": "2026-09-23T13:41:00Z"})
    result = evaluate(
        datetime(2026, 9, 23, 17, 20, tzinfo=timezone.utc),
        {
            "F-XAGENT-DISAGREE": xagent,
            "F-XMM-INVENTORY": xmm,
            "F-XVOL-SURFACE": xvol,
        },
    )
    by_id = {row["family_id"]: row for row in result["collectors"]}
    assert by_id["F-XAGENT-DISAGREE"]["status"] == "STALE_WARNING"
    assert by_id["F-XMM-INVENTORY"]["status"] == "FRESH"
    assert by_id["F-XVOL-SURFACE"]["status"] == "FRESH"
    assert result["hard_stale"] is False
    assert result["operational_only"] is True
    assert result["scientific_criteria_changed"] is False
    assert result["collection_cadence_changed"] is False
    assert result["runtime_mutation"] is False
    assert result["economic_outcomes_read"] is False


def test_family_mismatch_fails_closed(tmp_path: Path):
    xagent = tmp_path / "xagent.json"
    xmm = tmp_path / "xmm.json"
    xvol = tmp_path / "xvol.json"
    write(xagent, {"family_id": "WRONG", "generated_at_utc": "2026-09-23T15:38:00Z"})
    write(xmm, {"family_id": "F-XMM-INVENTORY", "latest_observed_at_utc": "2026-09-23T13:41:00Z"})
    write(xvol, {"family_id": "F-XVOL-SURFACE", "latest_observed_at_utc": "2026-09-23T13:41:00Z"})
    try:
        evaluate(
            datetime(2026, 9, 23, 17, 20, tzinfo=timezone.utc),
            {
                "F-XAGENT-DISAGREE": xagent,
                "F-XMM-INVENTORY": xmm,
                "F-XVOL-SURFACE": xvol,
            },
        )
    except ValueError:
        pass
    else:
        raise AssertionError("family mismatch must fail closed")
