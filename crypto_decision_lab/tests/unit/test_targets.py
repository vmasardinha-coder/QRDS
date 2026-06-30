import pytest

from crypto_decision_lab.targets.labels import (
    TARGET_LABEL_SCHEMA_VERSION,
    TargetLabelError,
    build_target_label_report,
    build_target_labels,
    is_regime_report_approved,
)
from crypto_decision_lab.targets.quality import (
    TARGET_QUALITY_SCHEMA_VERSION,
    build_target_quality_report,
    validate_target_rows,
)


def _feature_rows():
    closes = [100, 102, 105, 103, 108, 111]
    rows = []
    for i, close in enumerate(closes):
        rows.append({
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "close": close,
            "research_allowed": True,
            "operational_decision_allowed": False,
        })
    return rows


def _regime_report():
    return {
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "regime": "BULL",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
    }


def test_regime_report_approval_accepts_safe_report():
    assert is_regime_report_approved(_regime_report()) is True


def test_regime_report_approval_rejects_operational_flag():
    report = _regime_report()
    report["operational_decision_allowed"] = True
    assert is_regime_report_approved(report) is False


def test_build_target_labels_creates_future_returns():
    labels = build_target_labels(_feature_rows(), regime_report=_regime_report(), horizons=(1, 3))
    assert len(labels) == 3
    assert "future_return_h1" in labels[0]
    assert "future_return_h3" in labels[0]
    assert labels[0]["operational_decision_allowed"] is False


def test_build_target_labels_blocks_bad_regime_report():
    report = _regime_report()
    report["api_key_required"] = True
    with pytest.raises(TargetLabelError):
        build_target_labels(_feature_rows(), regime_report=report)


def test_target_rows_keep_research_only_flags():
    labels = build_target_labels(_feature_rows(), regime_report=_regime_report(), horizons=(1, 3))
    assert all(row["research_allowed"] is True for row in labels)
    assert all(row["operational_decision_allowed"] is False for row in labels)
    assert all(row["api_key_required"] is False for row in labels)
    assert all(row["orders_generated"] is False for row in labels)
    assert all(row["real_capital_used"] is False for row in labels)


def test_target_quality_report_schema_and_flags():
    labels = build_target_labels(_feature_rows(), regime_report=_regime_report(), horizons=(1, 3))
    quality = build_target_quality_report(
        labels,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
    )
    assert quality["schema"] == TARGET_QUALITY_SCHEMA_VERSION
    assert quality["target_quality_passed"] is True
    assert quality["operational_decision_allowed"] is False


def test_target_label_report_schema_and_flags():
    labels = build_target_labels(_feature_rows(), regime_report=_regime_report(), horizons=(1, 3))
    report = build_target_label_report(
        labels,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        regime="BULL",
    )
    assert report["schema"] == TARGET_LABEL_SCHEMA_VERSION
    assert report["label_row_count"] == len(labels)
    assert report["operational_decision_allowed"] is False


def test_validate_target_rows_flags_operational_true():
    labels = build_target_labels(_feature_rows(), regime_report=_regime_report(), horizons=(1, 3))
    labels[0]["operational_decision_allowed"] = True
    issues = validate_target_rows(labels)
    assert any(issue["code"] == "OPERATIONAL_FLAG_TRUE" for issue in issues)
