from __future__ import annotations

from crypto_decision_lab.reports.evidence_timeline import (
    EVIDENCE_TIMELINE_SCHEMA_VERSION,
    RESEARCH_ONLY_FALSE_FLAGS,
    build_evidence_timeline,
    build_fixture_evidence_reports,
    normalize_evidence_observations,
    validate_evidence_timeline,
)


def test_fixture_evidence_timeline_is_research_only() -> None:
    reports = build_fixture_evidence_reports(["BTC-USDT", "ETH-USDT"])
    timeline = build_evidence_timeline(reports)

    assert timeline["schema"] == EVIDENCE_TIMELINE_SCHEMA_VERSION
    assert timeline["asset_count"] == 2
    assert timeline["input_report_count"] == 2
    assert timeline["observation_count"] == 4
    assert timeline["gate_answer"].endswith("RESEARCH_ONLY")
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        assert timeline[flag] is False


def test_normalize_observations_from_quality_and_drilldown() -> None:
    reports = build_fixture_evidence_reports(["BTC-USDT"])
    observations = normalize_evidence_observations(reports)

    assert len(observations) == 2
    assert {item["gate_type"] for item in observations} == {"evidence_quality", "evidence_drilldown"}
    assert {item["symbol"] for item in observations} == {"BTC-USDT"}


def test_timeline_marks_insufficient_history_as_fail_or_watch() -> None:
    reports = build_fixture_evidence_reports(["BTC-USDT"])
    timeline = build_evidence_timeline(reports, min_observations=4)

    item = timeline["timelines"][0]
    assert item["history_status"] in {"FAIL", "WATCH"}
    assert "INSUFFICIENT_HISTORY_OBSERVATIONS" in " ".join(item["issues"])
    assert timeline["recommendation_generated"] is False
    assert timeline["orders_generated"] is False


def test_validate_evidence_timeline_accepts_research_payload() -> None:
    reports = build_fixture_evidence_reports(["BTC-USDT", "ETH-USDT"])
    timeline = build_evidence_timeline(reports)
    issues = validate_evidence_timeline(timeline)

    assert not [issue for issue in issues if issue.get("severity") == "error"]
