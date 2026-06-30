from crypto_decision_lab.regimes.diagnostics import (
    ALLOWED_REGIMES,
    REGIME_REPORT_SCHEMA_VERSION,
    build_regime_report,
    classify_market_regime,
)


def _rows_from_closes(closes):
    rows = []
    for i, close in enumerate(closes):
        prev = closes[i - 1] if i else None
        return_1 = None if prev is None else close / prev - 1.0
        sma_3 = None if i < 2 else sum(closes[i-2:i+1]) / 3
        sma_5 = None if i < 4 else sum(closes[i-4:i+1]) / 5
        rows.append({
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "close": close,
            "return_1": return_1,
            "sma_3": sma_3,
            "sma_5": sma_5,
            "research_allowed": True,
            "operational_decision_allowed": False,
        })
    return rows


def test_classifies_bull_regime():
    result = classify_market_regime(_rows_from_closes([100, 102, 104, 107, 110, 113]))
    assert result["regime"] == "BULL"
    assert result["operational_decision_allowed"] is False


def test_classifies_neutral_regime():
    result = classify_market_regime(_rows_from_closes([100, 101, 100.5, 101, 100.8, 101.2]))
    assert result["regime"] == "NEUTRAL"


def test_classifies_stress_regime():
    result = classify_market_regime(_rows_from_closes([100, 98, 95, 91, 88, 86]))
    assert result["regime"] in {"STRESS", "CRASH"}


def test_classifies_crash_regime():
    result = classify_market_regime(_rows_from_closes([100, 95, 80, 70, 60, 55]))
    assert result["regime"] == "CRASH"


def test_insufficient_data():
    result = classify_market_regime(_rows_from_closes([100, 101, 102]))
    assert result["regime"] == "INSUFFICIENT_DATA"


def test_regime_report_schema_and_flags():
    rows = _rows_from_closes([100, 102, 104, 107, 110, 113])
    report = build_regime_report(
        rows,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
    )

    assert report["schema"] == REGIME_REPORT_SCHEMA_VERSION
    assert report["regime"] in ALLOWED_REGIMES
    assert report["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
