import json

from tools.gate_btc_2_v2a_kcs_bybit_qualification_runner import parse_rows, qa


def test_parse_bybit_schema_and_qa_pass():
    raw = json.dumps({
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "category": "spot",
            "symbol": "KCSUSDT",
            "list": [
                ["1704153600000", "2.2", "3.2", "2", "2.5", "12", "30"],
                ["1704067200000", "1.5", "3", "1", "2", "10", "20"],
            ],
        },
    }).encode()
    rows = parse_rows(raw)
    result = qa(rows)
    assert result["rows"] == 2
    assert result["duplicates"] == 0
    assert result["internal_missing_days"] == 0
    assert result["bad_utc_day_alignment"] == 0
    assert result["bad_ohlc"] == 0
    assert result["bad_volume_or_turnover"] == 0
    assert result["qa_pass"] is True


def test_api_error_fails_closed():
    raw = json.dumps({"retCode": 10001, "retMsg": "bad request", "result": {"list": []}}).encode()
    try:
        parse_rows(raw)
    except ValueError as exc:
        assert "API error" in str(exc)
    else:
        raise AssertionError("API error must fail closed")


def test_unknown_schema_fails_closed():
    raw = json.dumps({"retCode": 0, "retMsg": "OK", "result": {"list": [["1", "2"]]}}).encode()
    try:
        parse_rows(raw)
    except ValueError as exc:
        assert "unexpected kline schema" in str(exc)
    else:
        raise AssertionError("unexpected schema must fail closed")


def test_missing_day_fails_qa():
    rows = [
        {"t": 1704067200000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10, "turnover": 15},
        {"t": 1704240000000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10, "turnover": 15},
    ]
    result = qa(rows)
    assert result["internal_missing_days"] == 1
    assert result["qa_pass"] is False
