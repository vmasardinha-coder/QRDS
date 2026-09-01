import json

from tools.gate_btc_2_v2a_nexo_gate_qualification_runner import parse_rows, qa


def test_parse_gate_schema_and_qa_pass():
    raw = json.dumps([
        ["1704067200", "10", "2", "3", "1", "1.5"],
        ["1704153600", "12", "2.5", "3.2", "2", "2.2"],
    ]).encode()
    rows = parse_rows(raw)
    result = qa(rows)
    assert result["rows"] == 2
    assert result["duplicates"] == 0
    assert result["internal_missing_days"] == 0
    assert result["bad_ohlc"] == 0
    assert result["bad_volume"] == 0
    assert result["qa_pass"] is True


def test_unknown_schema_fails_closed():
    raw = json.dumps({"label": "unexpected"}).encode()
    try:
        parse_rows(raw)
    except ValueError as exc:
        assert "non-list" in str(exc)
    else:
        raise AssertionError("unexpected schema must fail closed")


def test_missing_day_fails_qa():
    rows = [
        {"t": 1704067200, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10},
        {"t": 1704240000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10},
    ]
    result = qa(rows)
    assert result["internal_missing_days"] == 1
    assert result["qa_pass"] is False
