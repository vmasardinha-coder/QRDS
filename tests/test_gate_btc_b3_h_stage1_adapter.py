from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tools.gate_btc_b3_h_stage1_adapter import Stage1InputError, validate


def write_case(tmp_path: Path, *, start="2026-08-07 09:00", adjusted=False, bar_minutes=5, symbol="WINQ26"):
    ts = pd.date_range(start=start, periods=6, freq="5min")
    base = [135000, 135005, 135010, 135005, 135015, 135020]
    df = pd.DataFrame({
        "timestamp": ts.astype(str),
        "symbol": symbol,
        "open": base,
        "high": [x + 10 for x in base],
        "low": [x - 10 for x in base],
        "close": [x + 5 for x in base],
        "volume": [100, 120, 90, 110, 130, 140],
    })
    csv = tmp_path / "bars.csv"
    df.to_csv(csv, index=False)
    meta = {
        "source_type": "SYNTHETIC_CONTRACT_TEST_ONLY",
        "adjustment_mode": "BACK_ADJUSTED_CONTINUOUS" if adjusted else "EXPLICIT_CONTRACTS_NO_BACK_ADJUSTMENT",
        "bar_minutes": bar_minutes,
        "timezone": "America/Sao_Paulo",
        "roll_policy": "EXPLICIT_REAL_CONTRACT_STITCH",
    }
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps(meta), encoding="utf-8")
    return csv, metadata


def test_accepts_pre_h1_structural_m5_fixture(tmp_path):
    csv, metadata = write_case(tmp_path)
    df, att = validate(csv, metadata)
    assert len(df) == 6
    assert att.sessions == 1
    assert att.adjustment_mode == "EXPLICIT_CONTRACTS_NO_BACK_ADJUSTMENT"
    assert att.symbols == ("WINQ26",)
    payload = att.as_dict()
    assert payload["h1_economics_read"] is False
    assert payload["economics_computed"] is False
    assert payload["orders"] == 0 and payload["real_capital"] == 0


def test_rejects_h1_cutoff_or_later(tmp_path):
    csv, metadata = write_case(tmp_path, start="2026-08-10 09:00")
    with pytest.raises(Stage1InputError, match="H1_CUTOFF"):
        validate(csv, metadata)


def test_rejects_back_adjusted_continuous_series(tmp_path):
    csv, metadata = write_case(tmp_path, adjusted=True, symbol="WINFUT")
    with pytest.raises(Stage1InputError, match="ADJUSTED_OR_UNKNOWN"):
        validate(csv, metadata)


def test_rejects_non_m5_input(tmp_path):
    csv, metadata = write_case(tmp_path, bar_minutes=15)
    with pytest.raises(Stage1InputError, match="ONLY_M5"):
        validate(csv, metadata)


def test_rejects_economic_columns(tmp_path):
    csv, metadata = write_case(tmp_path)
    df = pd.read_csv(csv)
    df["pnl"] = 1.0
    df.to_csv(csv, index=False)
    with pytest.raises(Stage1InputError, match="ECONOMIC_OR_DECISION"):
        validate(csv, metadata)


def test_continuous_symbol_requires_reviewed_unadjusted_roll_policy(tmp_path):
    csv, metadata = write_case(tmp_path, symbol="WINFUT")
    meta = json.loads(metadata.read_text())
    meta["adjustment_mode"] = "UNADJUSTED_REAL_CONTRACT_PRICES"
    meta["roll_policy"] = "UNKNOWN"
    metadata.write_text(json.dumps(meta))
    with pytest.raises(Stage1InputError, match="ROLL_POLICY_NOT_APPROVED"):
        validate(csv, metadata)


def test_rejects_off_tick_prices(tmp_path):
    csv, metadata = write_case(tmp_path)
    df = pd.read_csv(csv)
    df.loc[0, "close"] = 135003
    df.to_csv(csv, index=False)
    with pytest.raises(Stage1InputError, match="OFF_WIN_TICK_GRID"):
        validate(csv, metadata)
