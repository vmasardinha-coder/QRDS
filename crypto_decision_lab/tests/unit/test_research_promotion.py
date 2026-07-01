from __future__ import annotations

from crypto_decision_lab.reports.research_promotion import (
    FORMAL_FUTURE_GATES,
    RESEARCH_ONLY_FALSE_FLAGS,
    RESEARCH_PROMOTION_SCHEMA_VERSION,
    build_fixture_promotion_reports,
    build_research_promotion_matrix,
    validate_research_promotion_matrix,
)


def test_fixture_research_promotion_matrix_is_research_only() -> None:
    reports = build_fixture_promotion_reports(["BTC-USDT", "ETH-USDT"])
    matrix = build_research_promotion_matrix(reports)

    assert matrix["schema"] == RESEARCH_PROMOTION_SCHEMA_VERSION
    assert matrix["asset_count"] == 2
    assert matrix["input_report_count"] == 3
    assert matrix["gate_answer"].endswith("RESEARCH_ONLY")
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        assert matrix[flag] is False


def test_research_promotion_matrix_contains_future_blocked_gates() -> None:
    reports = build_fixture_promotion_reports(["BTC-USDT"])
    matrix = build_research_promotion_matrix(reports)

    rows_by_gate = {row["gate_id"]: row for row in matrix["gate_rows"]}
    for gate in FORMAL_FUTURE_GATES:
        assert rows_by_gate[gate]["matrix_status"] == "BLOCKED_NOT_IMPLEMENTED"
        assert rows_by_gate[gate]["present"] is False
    assert matrix["orders_generated"] is False
    assert matrix["recommendation_generated"] is False


def test_research_promotion_symbol_matrix_tracks_all_current_gates() -> None:
    reports = build_fixture_promotion_reports(["BTC-USDT", "ETH-USDT", "SOL-USDT"])
    matrix = build_research_promotion_matrix(reports)

    assert matrix["symbols"] == ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    for row in matrix["symbol_rows"]:
        assert set(row["gate_scores"]) == {"evidence_quality", "evidence_drilldown", "evidence_timeline"}
        assert row["symbol_matrix_status"] in {"PASS", "WATCH", "FAIL"}


def test_research_promotion_validation_accepts_research_payload() -> None:
    reports = build_fixture_promotion_reports(["BTC-USDT", "ETH-USDT"])
    matrix = build_research_promotion_matrix(reports)
    issues = validate_research_promotion_matrix(matrix)

    assert not [issue for issue in issues if issue.get("severity") == "error"]
