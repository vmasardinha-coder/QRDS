import gzip

from tools.gate_btc_2_v2a_kcs_bybit_qualification_runner import parse_day


def test_parse_archive_schema_and_qa_pass():
    raw = gzip.compress(
        b"id,timestamp,price,volume,side\n"
        b"1,1704067200000,1.5,10,Buy\n"
        b"2,1704067201000,2.0,12,Sell\n"
    )
    result = parse_day("KCSUSDT_2024-01-01.csv.gz", "2024-01-01", raw)
    assert result["trade_rows"] == 2
    assert result["trade_order_monotonic"] is True
    assert result["open"] == 1.5
    assert result["close"] == 2.0
    assert result["base_volume"] == 22.0
    assert result["schema_variant"] == "BYBIT_SPOT_TRADES_V1"
    assert result["qa_pass"] is True


def test_explicit_rpi_variant_is_allowed_but_not_used_for_ohlcv():
    raw = gzip.compress(
        b"id,timestamp,price,volume,side,rpi\n"
        b"1,1704067200000,1.5,10,Buy,true\n"
        b"2,1704067201000,2.0,12,Sell,false\n"
    )
    result = parse_day("KCSUSDT_2024-01-01.csv.gz", "2024-01-01", raw)
    assert result["schema_variant"] == "BYBIT_SPOT_TRADES_V2_RPI"
    assert result["base_volume"] == 22.0


def test_unknown_schema_fails_closed():
    raw = gzip.compress(b"id,timestamp,price,volume,side,unknown\n1,1704067200000,1.5,10,Buy,x\n")
    try:
        parse_day("KCSUSDT_2024-01-01.csv.gz", "2024-01-01", raw)
    except ValueError as exc:
        assert "schema mismatch" in str(exc)
    else:
        raise AssertionError("unexpected schema must fail closed")


def test_day_spill_fails_closed():
    raw = gzip.compress(
        b"id,timestamp,price,volume,side\n"
        b"1,1704067200000,1.5,10,Buy\n"
        b"2,1704153600000,2.0,12,Sell\n"
    )
    try:
        parse_day("KCSUSDT_2024-01-01.csv.gz", "2024-01-01", raw)
    except ValueError as exc:
        assert "day spill" in str(exc)
    else:
        raise AssertionError("UTC day spill must fail closed")
