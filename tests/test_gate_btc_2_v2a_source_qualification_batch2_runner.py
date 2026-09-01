import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "gate_btc_2_v2a_source_qualification_batch2_runner.py"
spec = importlib.util.spec_from_file_location("v2a_batch2_runner", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_preregistered_source_and_identity_surface_are_frozen():
    assert mod.SOURCE["symbol"] == "MNT"
    assert mod.SOURCE["coin_id"] == "mantle"
    assert mod.SOURCE["provider"] == "Bybit"
    assert mod.SOURCE["market"] == "SPOT"
    assert mod.SOURCE["pair"] == "MNTUSDT"
    assert mod.SOURCE["base"].startswith("https://api.bybit.com/")


def test_provider_schema_parsing_and_instrument_surface():
    raw = b'{"retCode":0,"retMsg":"OK","result":{"list":[["86400000","10","12","9","11","1","10"]]}}'
    row = mod.parse_rows(raw)[0]
    assert row == {"t": 86400, "o": 10.0, "h": 12.0, "l": 9.0, "c": 11.0, "v": 1.0}
    instrument_raw = b'{"retCode":0,"retMsg":"OK","result":{"list":[{"symbol":"MNTUSDT","baseCoin":"MNT","quoteCoin":"USDT","status":"Trading"}]}}'
    parsed = mod.parse_instrument(instrument_raw)
    assert parsed["symbol"] == "MNTUSDT"
    assert parsed["baseCoin"] == "MNT"
    assert parsed["quoteCoin"] == "USDT"


def test_qa_fails_closed_on_gap_duplicate_and_bad_ohlc():
    good = [
        {"t": 0, "o": 10.0, "h": 12.0, "l": 9.0, "c": 11.0, "v": 1.0},
        {"t": mod.DAY, "o": 11.0, "h": 13.0, "l": 10.0, "c": 12.0, "v": 2.0},
    ]
    assert mod.qa(good)["qa_pass"] is True
    assert mod.qa(good + [dict(good[-1])])["qa_pass"] is False
    assert mod.qa([good[0], {**good[1], "t": 2 * mod.DAY}])["qa_pass"] is False
    assert mod.qa([good[0], {**good[1], "h": 10.5}])["qa_pass"] is False


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
        '"exact_asset_identity_admitted": False',
    ):
        assert required in text
