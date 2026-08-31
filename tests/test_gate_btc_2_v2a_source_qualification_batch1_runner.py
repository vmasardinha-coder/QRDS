import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "gate_btc_2_v2a_source_qualification_batch1_runner.py"
spec = importlib.util.spec_from_file_location("v2a_batch1_runner", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_preregistered_pairs_and_public_endpoints_are_frozen():
    assert mod.SOURCES["KCS"]["pair"] == "KCS-USDT"
    assert mod.SOURCES["BGB"]["pair"] == "BGBUSDT"
    assert mod.SOURCES["GT"]["pair"] == "GT_USDT"
    assert mod.SOURCES["KCS"]["base"].startswith("https://api.kucoin.com/")
    assert mod.SOURCES["BGB"]["base"].startswith("https://api.bitget.com/")
    assert mod.SOURCES["GT"]["base"].startswith("https://api.gateio.ws/")


def test_qa_fails_closed_on_gap_duplicate_and_bad_ohlc():
    good = [
        {"t": 0, "o": 10.0, "h": 12.0, "l": 9.0, "c": 11.0, "v": 1.0},
        {"t": mod.DAY, "o": 11.0, "h": 13.0, "l": 10.0, "c": 12.0, "v": 2.0},
    ]
    assert mod.qa(good)["qa_pass"] is True
    assert mod.qa(good + [dict(good[-1])])["qa_pass"] is False
    gap = [good[0], {**good[1], "t": 2 * mod.DAY}]
    assert mod.qa(gap)["qa_pass"] is False
    bad = [good[0], {**good[1], "h": 10.5}]
    assert mod.qa(bad)["qa_pass"] is False


def test_provider_schema_parsing():
    kucoin = b'{"code":"200000","data":[["86400","10","11","12","9","1","10"]]}'
    bitget = b'{"code":"00000","data":[["86400000","10","12","9","11","1","10"]]}'
    gate = b'[["86400","10","11","12","9","10","1"]]'
    for symbol, raw in (("KCS", kucoin), ("BGB", bitget), ("GT", gate)):
        row = mod.parse_rows(symbol, raw)[0]
        assert row["t"] == 86400
        assert row["o"] == 10.0
        assert row["h"] == 12.0
        assert row["l"] == 9.0
        assert row["c"] == 11.0
        assert row["v"] >= 0


def test_no_scientific_or_execution_credit_constants_in_source():
    text = MODULE_PATH.read_text(encoding="utf-8")
    for required in (
        '"scientific_credit": False',
        '"prospective_credit": False',
        '"dataset_sealed": False',
        '"promotion_allowed": False',
        '"engine_feed": False',
        '"orders": 0',
        '"real_capital_brl": 0',
        '"no_retune": True',
        '"no_backfill_credit": True',
        '"no_silent_source_substitution": True',
    ):
        assert required in text
