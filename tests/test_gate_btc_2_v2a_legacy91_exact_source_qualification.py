from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).parents[1] / "tools" / "gate_btc_2_v2a_legacy91_exact_source_qualification.py"
spec = importlib.util.spec_from_file_location("legacy91", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_provider_mapping_is_frozen_and_no_route_switch():
    cdd = m.provider_spec("BTC", "cdd")
    assert cdd == {"provider": "CRYPTODATADOWNLOAD_BINANCE_DAILY", "market_id": "binance", "pair": "BTCUSDT", "base": "BTC", "quote": "USDT"}
    b = m.provider_spec("ETH", "binance")
    assert b["provider"] == "BINANCE_SPOT" and b["pair"] == "ETHUSDT"
    o = m.provider_spec("SOL", "okx")
    assert o["provider"] == "OKX_SPOT" and o["pair"] == "SOL-USDT"


def test_qa_requires_exact_33_calendar_days_and_ohlc_invariant():
    rows = []
    d = m.WINDOW_START
    while d <= m.WINDOW_END:
        rows.append({"day": d.isoformat(), "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5})
        d += m.timedelta(days=1)
    q = m.qa(rows)
    assert q["qa_pass"] is True and q["daily_bucket_count"] == 33 and not q["missing_days"]
    q2 = m.qa(rows[:-1])
    assert q2["qa_pass"] is False and q2["missing_days"] == [m.WINDOW_END.isoformat()]
    bad = list(rows)
    bad[0] = dict(bad[0], high=1.0, close=1.5)
    assert m.qa(bad)["qa_pass"] is False


def test_binance_and_okx_parsers_preserve_utc_day():
    ts = int(m.datetime(2026, 8, 4, tzinfo=m.timezone.utc).timestamp() * 1000)
    b = m.parse_binance(json.dumps([[ts, "1", "2", "0.5", "1.5", "3"]]).encode())
    assert b[0]["day"] == "2026-08-04" and b[0]["close"] == 1.5
    o = m.parse_okx(json.dumps({"data": [[str(ts), "1", "2", "0.5", "1.5", "3", "3", "3", "1"]]}).encode())
    assert o[0]["day"] == "2026-08-04" and o[0]["close"] == 1.5


def test_summary_boundary_tokens_are_present_in_source():
    text = MODULE.read_text(encoding="utf-8")
    for token in (
        "research_only", "shadow_only", "not_approved", "engine_feed", "orders", "real_capital_brl",
        "no_retune", "no_backfill", "no_counter_reset", "no_silent_source_substitution", "fail_closed",
        "qualification_only", "source_admission_changed", "complete_registry_claimed", "collector_override_activation_allowed",
        "scientific_credit", "prospective_credit", "d0_credit",
    ):
        assert token in text
