from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools import gate_btc_v16b_feature_panel as core
from tools import gate_btc_v16b_source_bound_panel as bound


def _files(tmp_path: Path):
    dates = pd.date_range("2026-01-01", periods=180, freq="D")
    rows = []
    for i, d in enumerate(dates):
        rows.append({"date": d.date().isoformat(), "symbol": "BTCUSDT", "close": 40000*np.exp(i/1000), "volume_usd": 30_000_000+i})
        rows.append({"date": d.date().isoformat(), "symbol": "ALTUSDT", "close": 100*np.exp(i/900), "volume_usd": 20_000_000+i})
    daily = tmp_path / "daily.csv"; pd.DataFrame(rows).to_csv(daily, index=False)
    sig = pd.Timestamp("2026-05-28")
    universe = tmp_path / "universe.csv"
    pd.DataFrame([{"signal_date":sig.date().isoformat(),"symbol":"ALTUSDT","evidence_class":core.HISTORICAL_MODEL_ONLY,
                   "snapshot_effective_date":sig.date().isoformat(),"retrieved_at_utc":"2026-09-01T00:00:00Z",
                   "source_ref":"https://example.invalid/cmc","snapshot_sha256":"a"*64}]).to_csv(universe,index=False)
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"schema":"gate_btc.v16b.signal_market_source_manifest.v1",
        "daily_prices_sha256":core.sha256_file(daily),"weekly_universe_sha256":core.sha256_file(universe),
        "market_venue":"BINANCE_SPOT_USDT","benchmark":"BTCUSDT","contract_sha256":"b"*64,"signal_date":"2026-09-10"}))
    return daily, universe, source


def test_source_manifest_hashes_are_bound_into_panel_manifest(tmp_path):
    daily, universe, source = _files(tmp_path)
    out, manifest = bound.build(daily, universe, source)
    assert len(out) == 1
    assert manifest["signal_market_source_manifest_sha256"] == core.sha256_file(source)
    assert manifest["signal_market_source_contract_sha256"] == "b"*64


def test_source_manifest_daily_mismatch_fails_closed(tmp_path):
    daily, universe, source = _files(tmp_path)
    obj = json.loads(source.read_text()); obj["daily_prices_sha256"] = "0"*64; source.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="daily_prices_sha256 mismatch"):
        bound.build(daily, universe, source)
