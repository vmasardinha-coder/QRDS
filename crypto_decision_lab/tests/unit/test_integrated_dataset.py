import pytest

from crypto_decision_lab.datasets.research import (
    INTEGRATED_DATASET_SCHEMA_VERSION,
    IntegratedDatasetError,
    build_integrated_dataset_report,
    build_integrated_research_dataset,
    validate_integrated_rows,
)


def _candles():
    closes = [100, 102, 105, 103, 108, 111]
    rows = []
    for i, close in enumerate(closes):
        rows.append({
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 1000 + i,
        })
    return rows


def _features():
    rows = []
    for candle in _candles():
        rows.append({
            "ts": candle["ts"],
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "close": candle["close"],
            "return_1": 0.01,
            "log_return_1": 0.00995,
            "range_pct": 0.03,
            "body_pct": 0.01,
            "volume_change_1": 0.01,
            "sma_3": candle["close"],
            "sma_5": candle["close"],
            "volatility_3": 0.01,
            "research_allowed": True,
            "operational_decision_allowed": False,
        })
    return rows


def _targets():
    return [
        {
            "ts": _candles()[0]["ts"],
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "regime": "BULL",
            "close": 100,
            "future_return_h1": 0.02,
            "label_up_h1": True,
            "label_down_h1": False,
            "future_max_drawdown_h1": 0.0,
            "research_allowed": True,
            "operational_decision_allowed": False,
        },
        {
            "ts": _candles()[1]["ts"],
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "regime": "BULL",
            "close": 102,
            "future_return_h1": 0.01,
            "label_up_h1": False,
            "label_down_h1": False,
            "future_max_drawdown_h1": 0.0,
            "research_allowed": True,
            "operational_decision_allowed": False,
        },
    ]


def _dql_report():
    return {
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "dql_score": 95.0,
        "issue_summary": {"error_count": 0},
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
    }


def _regime_report():
    return {
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "regime": "BULL",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
    }


def test_build_integrated_dataset_joins_rows():
    rows = build_integrated_research_dataset(
        candles=_candles(),
        feature_rows=_features(),
        target_labels=_targets(),
        dql_report=_dql_report(),
        regime_report=_regime_report(),
    )

    assert len(rows) == 2
    assert rows[0]["candle_close"] == 100
    assert rows[0]["dql_score"] == 95.0
    assert rows[0]["regime"] == "BULL"
    assert rows[0]["future_return_h1"] == 0.02
    assert rows[0]["operational_decision_allowed"] is False


def test_build_integrated_dataset_blocks_bad_dql():
    dql = _dql_report()
    dql["issue_summary"]["error_count"] = 1

    with pytest.raises(IntegratedDatasetError):
        build_integrated_research_dataset(
            candles=_candles(),
            feature_rows=_features(),
            target_labels=_targets(),
            dql_report=dql,
            regime_report=_regime_report(),
        )


def test_build_integrated_dataset_blocks_operational_regime():
    regime = _regime_report()
    regime["operational_decision_allowed"] = True

    with pytest.raises(IntegratedDatasetError):
        build_integrated_research_dataset(
            candles=_candles(),
            feature_rows=_features(),
            target_labels=_targets(),
            dql_report=_dql_report(),
            regime_report=regime,
        )


def test_validate_integrated_rows_passes_clean_rows():
    rows = build_integrated_research_dataset(
        candles=_candles(),
        feature_rows=_features(),
        target_labels=_targets(),
        dql_report=_dql_report(),
        regime_report=_regime_report(),
    )

    assert validate_integrated_rows(rows) == []


def test_validate_integrated_rows_flags_operational_true():
    rows = build_integrated_research_dataset(
        candles=_candles(),
        feature_rows=_features(),
        target_labels=_targets(),
        dql_report=_dql_report(),
        regime_report=_regime_report(),
    )
    rows[0]["operational_decision_allowed"] = True

    issues = validate_integrated_rows(rows)
    assert any(issue["code"] == "OPERATIONAL_FLAG_TRUE" for issue in issues)


def test_integrated_dataset_report_schema_and_flags():
    rows = build_integrated_research_dataset(
        candles=_candles(),
        feature_rows=_features(),
        target_labels=_targets(),
        dql_report=_dql_report(),
        regime_report=_regime_report(),
    )

    report = build_integrated_dataset_report(
        rows,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
    )

    assert report["schema"] == INTEGRATED_DATASET_SCHEMA_VERSION
    assert report["dataset_quality_passed"] is True
    assert report["row_count"] == len(rows)
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
