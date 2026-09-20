import json
from pathlib import Path

from tools.gate_btc_factory.grammar_source_cost_intake import build
from tools.gate_btc_factory.grammar_source_cost_qualifier import qualify


def _prereg(*, frozen_semantics=None):
    row = {
        "schema": "qrds.factory.grammar_scout_separate_prereg.v1",
        "family_id": "XAGRAMMAR_TEST000000",
        "grammar_signature": "a" * 64,
        "channel_id": "TEST_CHANNEL",
        "mechanism": "Outcome-blind test mechanism.",
        "required_new_data": ["official test data"],
        "official_free_source_candidates": ["OFFICIAL_TEST"],
        "status": "PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION",
        "source_qualification_required": True,
        "cost_applicability_required": True,
        "economics_read": False,
        "historical_testing_started": False,
    }
    if frozen_semantics is not None:
        row["frozen_semantics"] = frozen_semantics
    return row


def _protocol():
    return {
        "schema": "qrds.factory.grammar_source_cost_qualification_protocol.v1",
        "frozen_before_outcomes": True,
        "safety": {"FAIL_CLOSED": True},
    }


def test_legacy_prereg_without_frozen_semantics_is_nonterminally_blocked(tmp_path: Path):
    prereg_dir = tmp_path / "prereg"
    prereg_dir.mkdir()
    (prereg_dir / "XAGRAMMAR_TEST000000.json").write_text(json.dumps(_prereg()), encoding="utf-8")

    intake = build(prereg_dir)
    assert intake["semantic_ready_count"] == 0
    assert intake["blocked_semantics_count"] == 1
    family = intake["families"][0]
    assert family["status"] == "BLOCKED_PREREG_SEMANTICS_UNDECIDABLE"
    assert family["semantic_preregistration_complete"] is False
    assert family["economics_read"] is False
    assert family["historical_testing_started"] is False

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "XAGRAMMAR_TEST000000.json").write_text("{}", encoding="utf-8")
    result = qualify(intake, _protocol(), evidence_dir)
    assert result["qualified_count"] == 0
    assert result["waiting_count"] == 0
    assert result["blocked_semantics_count"] == 1
    assert result["rejected_count"] == 0
    assert result["families"][0]["status"] == "BLOCKED_PREREG_SEMANTICS_UNDECIDABLE"


def test_future_prereg_with_frozen_semantics_reaches_source_cost_gate(tmp_path: Path):
    prereg_dir = tmp_path / "prereg"
    prereg_dir.mkdir()
    semantics = {
        "feature": "FROZEN_TEST_FEATURE",
        "window": "FROZEN_TEST_WINDOW",
        "lookback": "FROZEN_TEST_LOOKBACK",
        "target": "FROZEN_TEST_TARGET",
    }
    (prereg_dir / "XAGRAMMAR_TEST000000.json").write_text(
        json.dumps(_prereg(frozen_semantics=semantics)), encoding="utf-8"
    )

    intake = build(prereg_dir)
    assert intake["semantic_ready_count"] == 1
    assert intake["blocked_semantics_count"] == 0
    family = intake["families"][0]
    assert family["status"] == "QUEUED_FOR_SOURCE_COST_QUALIFICATION"
    assert family["frozen_semantics"] == semantics

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    result = qualify(intake, _protocol(), evidence_dir)
    assert result["waiting_count"] == 1
    assert result["blocked_semantics_count"] == 0
    assert result["families"][0]["status"] == "WAITING_SOURCE_COST_EVIDENCE"
