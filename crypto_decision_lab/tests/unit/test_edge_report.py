import pytest

from crypto_decision_lab.reports.edge import (
    EDGE_REPORT_SCHEMA_VERSION,
    EDGE_STATUS_NO_EVIDENCE,
    EDGE_STATUS_PROMISING,
    EDGE_STATUS_WEAK,
    EdgeReportError,
    build_edge_report_v1,
    score_research_edge,
    summarize_edge_report_for_console,
    validate_edge_report_v1,
)


def _backtest_report(mean_total_return=0.05, worst_max_drawdown=-0.05, split_count=3, active_events=6):
    return {
        "schema": "qrds.backtest_walk_forward_report.v1",
        "return_column": "future_return_h1",
        "dataset_row_count": 12,
        "split_count": split_count,
        "aggregate": {
            "split_count": split_count,
            "mean_total_return": mean_total_return,
            "min_total_return": -0.01,
            "max_total_return": 0.08,
            "mean_max_drawdown": -0.02,
            "worst_max_drawdown": worst_max_drawdown,
            "total_active_events": active_events,
        },
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
    }


def _baseline_report():
    return {
        "schema": "qrds.baseline_walk_forward_report.v1",
        "split_count": 3,
        "aggregate": {
            "split_count": 3,
            "mean_mae": 0.01,
            "mean_rmse": 0.02,
            "mean_accuracy": None,
        },
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
    }


def test_score_research_edge_promising():
    score = score_research_edge(
        mean_total_return=0.05,
        worst_max_drawdown=-0.05,
        split_count=3,
        total_active_events=6,
    )

    assert score["edge_status"] == EDGE_STATUS_PROMISING
    assert score["score"] == 4.0


def test_score_research_edge_weak_or_no_evidence():
    weak = score_research_edge(
        mean_total_return=-0.01,
        worst_max_drawdown=-0.05,
        split_count=3,
        total_active_events=6,
    )
    no_evidence = score_research_edge(
        mean_total_return=-0.01,
        worst_max_drawdown=-0.50,
        split_count=1,
        total_active_events=0,
    )

    assert weak["edge_status"] == EDGE_STATUS_WEAK
    assert no_evidence["edge_status"] == EDGE_STATUS_NO_EVIDENCE


def test_build_edge_report_v1():
    report = build_edge_report_v1(
        backtest_report=_backtest_report(),
        baseline_report=_baseline_report(),
        notes="unit test",
    )

    assert report["schema"] == EDGE_REPORT_SCHEMA_VERSION
    assert report["edge_status"] == EDGE_STATUS_PROMISING
    assert report["operational_decision_allowed"] is False
    assert report["orders_allowed"] is False
    assert report["trading_signal_generated"] is False
    assert report["executable_signal_generated"] is False
    assert report["recommendation_generated"] is False
    assert validate_edge_report_v1(report) == []


def test_build_edge_report_blocks_unsafe_artifact():
    payload = _backtest_report()
    payload["orders_generated"] = True

    with pytest.raises(EdgeReportError):
        build_edge_report_v1(backtest_report=payload)


def test_summarize_edge_report_for_console():
    report = build_edge_report_v1(backtest_report=_backtest_report())
    summary = summarize_edge_report_for_console(report)

    assert summary["edge_status"] == EDGE_STATUS_PROMISING
    assert summary["validation_error_count"] == 0
    assert summary["operational_decision_allowed"] is False
    assert summary["recommendation_generated"] is False
