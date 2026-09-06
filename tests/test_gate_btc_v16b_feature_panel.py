from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools import gate_btc_v16b_feature_panel as panel


def _inputs(tmp_path: Path, evidence_class: str, retrieved_at: str):
    dates = pd.date_range("2025-01-01", periods=240, freq="D")
    # deterministic non-collinear paths so beta/correlation/residual features exist
    t = np.arange(len(dates), dtype=float)
    btc = 40000.0 * np.exp(0.0010 * t + 0.015 * np.sin(t / 11.0))
    alt = 100.0 * np.exp(0.0014 * t + 0.022 * np.sin(t / 7.0) + 0.006 * np.cos(t / 17.0))
    rows = []
    for d, b, a in zip(dates, btc, alt):
        rows.append({"date": d.date().isoformat(), "symbol": "BTCUSDT", "close": b, "volume_usd": 1_000_000 + 1000 * int((d-dates[0]).days)})
        rows.append({"date": d.date().isoformat(), "symbol": "ALTUSDT", "close": a, "volume_usd": 500_000 + 750 * int((d-dates[0]).days)})
    daily = tmp_path / "daily.csv"
    pd.DataFrame(rows).to_csv(daily, index=False)

    signal = dates[210]
    # select the next Thursday while keeping ample history and a realized label
    while signal.weekday() != 3:
        signal += pd.Timedelta(days=1)
    universe = tmp_path / "universe.csv"
    pd.DataFrame([{
        "signal_date": signal.date().isoformat(),
        "symbol": "ALTUSDT",
        "evidence_class": evidence_class,
        "snapshot_effective_date": signal.date().isoformat(),
        "retrieved_at_utc": retrieved_at,
        "source_ref": f"https://example.invalid/historical/{signal:%Y%m%d}",
        "snapshot_sha256": "a" * 64,
    }]).to_csv(universe, index=False)
    return daily, universe, signal


def test_frozen_feature_contract_exact():
    assert panel.FROZEN_FEATURES == list(panel.core.FEATURES)
    assert len(panel.FROZEN_FEATURES) == 18


def test_historical_official_snapshot_retrieved_late_is_training_only(tmp_path):
    daily, universe, _ = _inputs(tmp_path, panel.HISTORICAL_MODEL_ONLY, "2026-09-06T06:00:00Z")
    out, manifest = panel.build_panel(daily, universe)
    assert bool(out.loc[0, "feature_ok"])
    assert not bool(out.loc[0, "prospective_eligible"])
    assert int(out.loc[0, "prospective_credit"]) == 0
    assert manifest["prospective_credit"] == 0
    assert manifest["missed_cycle_reconstruction"] is False


def test_late_current_prospective_pit_fails_closed(tmp_path):
    daily, universe, signal = _inputs(tmp_path, panel.PROSPECTIVE_PIT, "2026-09-06T06:00:00Z")
    assert pd.Timestamp(signal) < pd.Timestamp("2026-09-06")
    with pytest.raises(ValueError, match="retrieved after signal cutoff"):
        panel.build_panel(daily, universe)


def test_anti_lookahead_future_mutation_does_not_change_signal_features(tmp_path):
    daily, universe, signal = _inputs(tmp_path, panel.HISTORICAL_MODEL_ONLY, "2026-09-06T06:00:00Z")
    first, _ = panel.build_panel(daily, universe)
    source = pd.read_csv(daily)
    mask = pd.to_datetime(source["date"]) > pd.Timestamp(signal)
    source.loc[mask & source["symbol"].eq("ALTUSDT"), "close"] *= 9.0
    source.loc[mask & source["symbol"].eq("ALTUSDT"), "volume_usd"] *= 13.0
    mutated = tmp_path / "daily_mutated.csv"
    source.to_csv(mutated, index=False)
    second, _ = panel.build_panel(mutated, universe)
    np.testing.assert_allclose(
        first.loc[0, panel.FROZEN_FEATURES].astype(float).to_numpy(),
        second.loc[0, panel.FROZEN_FEATURES].astype(float).to_numpy(),
        rtol=0,
        atol=0,
    )


def test_unresolved_future_label_is_never_synthesized(tmp_path):
    daily, universe, signal = _inputs(tmp_path, panel.HISTORICAL_MODEL_ONLY, "2026-09-06T06:00:00Z")
    source = pd.read_csv(daily)
    cutoff = (pd.Timestamp(signal) + pd.Timedelta(days=2)).date().isoformat()
    source = source[source["date"] <= cutoff]
    truncated = tmp_path / "daily_truncated.csv"
    source.to_csv(truncated, index=False)
    out, _ = panel.build_panel(truncated, universe)
    assert pd.isna(out.loc[0, "fwd_ret"])
    assert bool(out.loc[0, "feature_ok"])


def test_deterministic_panel_values(tmp_path):
    daily, universe, _ = _inputs(tmp_path, panel.HISTORICAL_MODEL_ONLY, "2026-09-06T06:00:00Z")
    a, ma = panel.build_panel(daily, universe)
    b, mb = panel.build_panel(daily, universe)
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    assert ma == mb
