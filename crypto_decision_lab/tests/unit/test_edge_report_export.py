import pytest

from crypto_decision_lab.reports.edge import build_edge_report_v1
from crypto_decision_lab.reports.export import (
    EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION,
    EdgeReportExportError,
    assert_edge_report_exportable,
    compute_json_payload_sha256,
    load_edge_report_artifacts,
    validate_edge_report_export_index,
    write_edge_report_artifacts,
)


def _backtest_report():
    return {
        "schema": "qrds.backtest_walk_forward_report.v1",
        "return_column": "future_return_h1",
        "dataset_row_count": 12,
        "split_count": 3,
        "aggregate": {
            "split_count": 3,
            "mean_total_return": 0.05,
            "min_total_return": -0.01,
            "max_total_return": 0.08,
            "mean_max_drawdown": -0.02,
            "worst_max_drawdown": -0.05,
            "total_active_events": 6,
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


def test_compute_json_payload_sha256_is_stable():
    payload = {"b": 2, "a": 1}

    assert compute_json_payload_sha256(payload) == compute_json_payload_sha256({"a": 1, "b": 2})


def test_assert_edge_report_exportable():
    edge_report = build_edge_report_v1(backtest_report=_backtest_report())

    assert_edge_report_exportable(edge_report)


def test_assert_edge_report_exportable_blocks_unsafe():
    edge_report = build_edge_report_v1(backtest_report=_backtest_report())
    edge_report["recommendation_generated"] = True

    with pytest.raises(EdgeReportExportError):
        assert_edge_report_exportable(edge_report)


def test_write_and_load_edge_report_artifacts(tmp_path):
    edge_report = build_edge_report_v1(backtest_report=_backtest_report())
    index = write_edge_report_artifacts(
        edge_report,
        output_dir=tmp_path,
        report_id="unit-edge",
    )
    loaded = load_edge_report_artifacts(index["index_path"])

    assert index["schema"] == EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION
    assert index["edge_status"] == edge_report["edge_status"]
    assert validate_edge_report_export_index(index) == []
    assert loaded["edge_report"]["schema"] == edge_report["schema"]
    assert loaded["summary"]["edge_status"] == edge_report["edge_status"]
    assert loaded["index"]["operational_decision_allowed"] is False


def test_validate_edge_report_export_index_flags_missing_file(tmp_path):
    edge_report = build_edge_report_v1(backtest_report=_backtest_report())
    index = write_edge_report_artifacts(
        edge_report,
        output_dir=tmp_path,
        report_id="unit-edge",
    )
    index["summary_path"] = str(tmp_path / "missing.json")

    issues = validate_edge_report_export_index(index)

    assert any(issue["code"] == "MISSING_EDGE_EXPORT_FILE" for issue in issues)
