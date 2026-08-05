from __future__ import annotations

import io
import zipfile
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from collect_multisource import analyze_price, parse_kline_zip, source_window_classification


def series(start: str, prices: list[float], step_days: int = 1) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range(start, periods=len(prices), freq=f"{step_days}D"),
        "price": prices,
    })


def test_no_90_drawdown():
    x = np.linspace(100, 30, 1500)
    r = analyze_price(series("2020-01-01", x.tolist()), robust=False)
    assert r["status"] == "QUANT_SURVIVOR_NO_90_DRAWDOWN"


def test_death_after_three_years_nonrecovery():
    prices = [100.0] * 100 + [9.0] * 1200
    r = analyze_price(series("2020-01-01", prices), robust=False)
    assert r["status"] == "QUANT_DEATH"
    assert r["persistent_below30_days"] >= 1095


def test_recovered_is_not_death():
    prices = [100.0] * 100 + [5.0] * 500 + [35.0] * 900
    r = analyze_price(series("2020-01-01", prices), robust=False)
    assert r["status"] == "QUANT_RECOVERED"


def test_provisional_clock():
    prices = [100.0] * 100 + [8.0] * 400
    r = analyze_price(series("2025-01-01", prices), robust=False)
    assert r["status"] == "QUANT_DEATH_PROVISIONAL"


def test_source_window_survivor_is_censored_without_inception():
    r = {"status": "QUANT_SURVIVOR_NO_90_DRAWDOWN", "reason": "NO_DRAWDOWN_GE_90"}
    st, reason, resolved = source_window_classification(r, "A_SPOT_STABLE", False)
    assert st == "QUANT_SOURCE_WINDOW_NO_90"
    assert not resolved
    assert "INCEPTION_NOT_PROVEN" in reason


def test_observed_death_is_valid_in_source_window():
    r = {"status": "QUANT_DEATH", "reason": "x"}
    st, _, resolved = source_window_classification(r, "A_SPOT_STABLE", False)
    assert st == "QUANT_DEATH"
    assert resolved


def test_perpetual_proxy_is_not_cagr_eligible_status():
    r = {"status": "QUANT_DEATH", "reason": "x"}
    st, reason, resolved = source_window_classification(r, "C_PERPETUAL_PROXY", False)
    assert st == "QUANT_DEATH_PROXY"
    assert not resolved
    assert "PERPETUAL_PROXY" in reason


def test_binance_zip_parser_handles_ms_and_us():
    rows = [
        "1577836800000,1,2,0.5,1.5,10,1577923199999,15,1,5,7.5,0",
        "1735689600000000,2,3,1,2.5,10,1735775999999999,25,1,5,12.5,0",
    ]
    payload = "\n".join(rows).encode()
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("PAIR-1d.csv", payload)
    frame, meta = parse_kline_zip(bio.getvalue(), "dummy.zip")
    assert meta["status"] == "OK"
    assert len(frame) == 2
    assert frame.price.tolist() == [1.5, 2.5]
    assert frame.date.dt.year.tolist() == [2020, 2025]
