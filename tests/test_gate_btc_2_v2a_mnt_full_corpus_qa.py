import importlib.util,gzip
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"tools"/"gate_btc_2_v2a_mnt_full_corpus_qa.py"
s=importlib.util.spec_from_file_location("mnt_full",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

def test_parser_accepts_exact_day_and_derives_valid_ohlcv():
    raw=gzip.compress(b"id,timestamp,price,volume,side\n1,1690156800000,1.0,2.0,Buy\n2,1690156801000,2.0,3.0,Sell\n")
    r=m.parse_day("MNTUSDT_2023-07-24.csv.gz","2023-07-24",raw)
    assert r["qa_pass"] is True and r["open"]==1.0 and r["close"]==2.0 and r["base_volume"]==5.0
    assert r["schema_variant"]=="BYBIT_SPOT_TRADES_V1"

def test_parser_accepts_explicit_rpi_schema_variant_without_using_rpi_for_ohlcv():
    raw=gzip.compress(b"id,timestamp,price,volume,side,rpi\n1,1690156800000,1.0,2.0,Buy,true\n2,1690156801000,2.0,3.0,Sell,false\n")
    r=m.parse_day("MNTUSDT_2023-07-24.csv.gz","2023-07-24",raw)
    assert r["qa_pass"] is True and r["open"]==1.0 and r["close"]==2.0 and r["base_volume"]==5.0
    assert r["schema_variant"]=="BYBIT_SPOT_TRADES_V2_RPI" and r["schema_fields"][-1]=="rpi"

def test_parser_rejects_unknown_schema_variant_fail_closed():
    raw=gzip.compress(b"id,timestamp,price,volume,side,rpi,unknown\n1,1690156800000,1.0,2.0,Buy,true,x\n")
    try:m.parse_day("MNTUSDT_2023-07-24.csv.gz","2023-07-24",raw)
    except ValueError as e: assert "schema mismatch" in str(e)
    else: raise AssertionError("unknown source schema must fail closed")

def test_parser_fails_on_day_spill():
    raw=gzip.compress(b"id,timestamp,price,volume,side\n1,1690156800000,1.0,2.0,Buy\n2,1690243200000,2.0,3.0,Sell\n")
    try:m.parse_day("MNTUSDT_2023-07-24.csv.gz","2023-07-24",raw)
    except ValueError as e: assert "spill" in str(e)
    else: raise AssertionError("must fail closed")

def test_safety_constants_are_explicit():
    t=P.read_text()
    for x in ('"scientific_credit":False','"prospective_credit":False','"dataset_sealed":False','"engine_feed":False','"orders":0','"real_capital_brl":0','"no_retune":True','"no_backfill":True','"no_silent_source_substitution":True','"fail_closed":True'):
        assert x in t
