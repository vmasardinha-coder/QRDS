from __future__ import annotations

import pandas as pd
import pytest

from tools import gate_btc_v16b_signal_source as src


def _cmc():
    return pd.DataFrame([
        {"id": 1, "symbol": "BTC", "slug": "bitcoin", "cmc_rank": 1},
        {"id": 2, "symbol": "ETH", "slug": "ethereum", "cmc_rank": 2},
        {"id": 3, "symbol": "ALT", "slug": "alt-one", "cmc_rank": 3},
        {"id": 4, "symbol": "DUP", "slug": "dup-one", "cmc_rank": 4},
        {"id": 5, "symbol": "DUP", "slug": "dup-two", "cmc_rank": 5},
    ])


def _exchange():
    return {"symbols": [
        {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
        {"symbol": "ETHUSDT", "baseAsset": "ETH", "quoteAsset": "USDT", "status": "TRADING"},
        {"symbol": "ALTUSDC", "baseAsset": "ALT", "quoteAsset": "USDC", "status": "TRADING"},
        {"symbol": "DUPUSDT", "baseAsset": "DUP", "quoteAsset": "USDT", "status": "TRADING"},
        {"symbol": "OLDUSDT", "baseAsset": "OLD", "quoteAsset": "USDT", "status": "BREAK"},
    ]}


def test_mapping_is_exact_baseasset_usdt_and_never_appends_quote():
    m = src.build_mapping(_cmc(), _exchange(), pd.Timestamp("2026-09-10"))
    got = {r.cmc_symbol + ":" + r.cmc_slug: (r.mapping_status, r.market_symbol, r.mapping_reason) for r in m.itertuples()}
    assert got["BTC:bitcoin"][:2] == ("MAPPED", "BTCUSDT")
    assert got["ETH:ethereum"][:2] == ("MAPPED", "ETHUSDT")
    assert got["ALT:alt-one"] == ("UNMAPPED", "", "NO_EXACT_BINANCE_SPOT_USDT_BASEASSET_MATCH")
    assert got["DUP:dup-one"][0] == "UNMAPPED"
    assert got["DUP:dup-two"][0] == "UNMAPPED"


def test_market_not_in_cmc_never_enters_mapping():
    m = src.build_mapping(_cmc().iloc[:2], _exchange(), pd.Timestamp("2026-09-10"))
    assert set(m.market_symbol) == {"BTCUSDT", "ETHUSDT"}
    assert "OLDUSDT" not in set(m.market_symbol)


def test_kline_normalization_uses_quote_volume_and_drops_future_bar():
    sig = pd.Timestamp("2026-09-10")
    day0 = int(pd.Timestamp("2026-09-09T00:00:00Z").timestamp() * 1000)
    day1 = int(pd.Timestamp("2026-09-10T00:00:00Z").timestamp() * 1000)
    day2 = int(pd.Timestamp("2026-09-11T00:00:00Z").timestamp() * 1000)
    rows = [
        [day0, "1", "2", "1", "1.5", "100", day1 - 1, "15000000", 1, "0", "0", "0"],
        [day1, "1.5", "2", "1", "1.75", "200", day2 - 1, "25000000", 1, "0", "0", "0"],
        [day2, "1.75", "3", "1", "2.0", "300", day2 + 86400000 - 1, "35000000", 1, "0", "0", "0"],
    ]
    d = src.normalize_klines("BTCUSDT", rows, sig)
    assert list(d.date) == ["2026-09-09", "2026-09-10"]
    assert list(d.volume_usd) == [15000000.0, 25000000.0]
    assert list(d.close) == [1.5, 1.75]


def test_invalid_or_empty_kline_fails_closed():
    with pytest.raises(ValueError):
        src.normalize_klines("BTCUSDT", [], pd.Timestamp("2026-09-10"))
    with pytest.raises(ValueError):
        src.normalize_klines("BTCUSDT", [[1, 2]], pd.Timestamp("2026-09-10"))


def test_non_thursday_live_build_rejected_before_network(tmp_path):
    snap = tmp_path / "cmc.json"
    snap.write_text('[{"id":1,"symbol":"BTC","slug":"bitcoin","cmc_rank":1}]')
    ev = tmp_path / "ev.json"
    ev.write_text('{}')
    with pytest.raises(ValueError, match="Thursday"):
        src.build_live(snap, ev, pd.Timestamp("2026-09-09"), tmp_path / "out")
