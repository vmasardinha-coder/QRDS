#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

LOCK_ACTIVATION_GAIN = 0.20
LOCK_GIVEBACK_FRACTION = 0.50
DEFAULT_SEED = 20260808
DEFAULT_REPS = 10_000
EXPECTED_PHASE1_PROTOCOL = "EXTERNAL_MONTHLY_PIT_TOP150_STRICT_NEXT_BAR"
EXPECTED_CANONICAL_SHA = "6eea7a1b8caef7ff19188ab32f32f2e1a26eef1a06027764b720b3d351e9e804"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def first_after(series: pd.Series, day: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    eligible = series[series.index > day]
    require(not eligible.empty, f"no validated price after {day.date()}")
    return pd.Timestamp(eligible.index[0]), float(eligible.iloc[0])


def trade_outcome(series: pd.Series, signal_date: pd.Timestamp, boundary: pd.Timestamp) -> dict:
    """Execution-consistent monthly baseline and LOCK_50 for one selected alt.

    Entry occurs on the first validated daily close strictly after the signal date.
    A LOCK trigger is observed only on a confirmed daily close and its executable
    virtual exit occurs on the first validated daily close strictly after trigger.
    The monthly baseline exits on the first validated daily close strictly after
    the next signal boundary.
    """
    series = series.sort_index().astype(float)
    entry_date, entry_price = first_after(series, signal_date)
    baseline_exit_date, baseline_exit_price = first_after(series, boundary)
    baseline_return = baseline_exit_price / entry_price - 1.0

    forward = series[(series.index > entry_date) & (series.index <= boundary)]
    peak_gain = float("-inf")
    activated = False
    trigger_date = None
    for day, price in forward.items():
        current_gain = float(price / entry_price - 1.0)
        peak_gain = max(peak_gain, current_gain)
        activated = activated or peak_gain >= LOCK_ACTIVATION_GAIN
        if activated and current_gain <= peak_gain * (1.0 - LOCK_GIVEBACK_FRACTION):
            trigger_date = pd.Timestamp(day)
            break

    if trigger_date is None:
        executable_exit_date = baseline_exit_date
        executable_return = baseline_return
        same_close_exit_date = baseline_exit_date
        same_close_return = baseline_return
    else:
        executable_exit_date, executable_exit_price = first_after(series, trigger_date)
        executable_return = executable_exit_price / entry_price - 1.0
        same_close_exit_date = trigger_date
        same_close_return = float(series.loc[trigger_date] / entry_price - 1.0)

    path = series[(series.index >= entry_date) & (series.index <= boundary)] / entry_price - 1.0
    require(not path.empty, "empty execution path")
    return {
        "entry_date": entry_date,
        "baseline_exit_date": baseline_exit_date,
        "baseline_return": float(baseline_return),
        "trigger_date": trigger_date,
        "lock50_exec_exit_date": executable_exit_date,
        "lock50_exec_return": float(executable_return),
        "lock50_same_close_exit_date": same_close_exit_date,
        "lock50_same_close_return": float(same_close_return),
        "mfe": float(path.max()),
        "mae": float(path.min()),
    }


def build_trades(selections: pd.DataFrame, coverage: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    selections = selections.copy()
    coverage = coverage.copy()
    history = history.copy()
    selections["signal_date"] = pd.to_datetime(selections["signal_date"])
    coverage["signal_date"] = pd.to_datetime(coverage["signal_date"])
    history["date"] = pd.to_datetime(history["date"])

    selections = selections.merge(
        coverage[["signal_date", "coverage_ratio", "gate_95"]],
        on="signal_date",
        how="left",
        validate="many_to_one",
    )
    require(selections["gate_95"].notna().all(), "selection/coverage calendar mismatch")
    all_signal_dates = sorted(selections["signal_date"].unique())
    next_signal = {
        pd.Timestamp(all_signal_dates[i]): pd.Timestamp(all_signal_dates[i + 1])
        for i in range(len(all_signal_dates) - 1)
    }
    prices = {
        symbol: frame.sort_values("date").drop_duplicates("date", keep="last").set_index("date")["close_usd"].astype(float)
        for symbol, frame in history.groupby("symbol")
    }

    rows = []
    eligible = selections[selections["gate_95"].astype(bool)]
    for record in eligible.itertuples(index=False):
        signal_date = pd.Timestamp(record.signal_date)
        if signal_date not in next_signal:
            continue
        boundary = next_signal[signal_date]
        picks = [x for x in str(record.picks or "").split(";") if x and x != "nan"]
        require(picks, f"empty picks {signal_date.date()} {record.strategy}")
        for symbol in picks:
            require(symbol in prices, f"missing selected symbol history {symbol}")
            outcome = trade_outcome(prices[symbol], signal_date, boundary)
            rows.append({
                "signal_date": signal_date,
                "boundary_date": boundary,
                "strategy": record.strategy,
                "regime": record.regime,
                "symbol": symbol,
                "coverage_ratio": float(record.coverage_ratio),
                **outcome,
            })
    trades = pd.DataFrame(rows)
    require(not trades.empty, "no execution-consistent trades")
    return trades


def summarize(trades: pd.DataFrame, reps: int, seed: int):
    signal = (
        trades.groupby(["signal_date", "strategy", "regime"], as_index=False)
        .agg(
            month_end_exec=("baseline_return", "mean"),
            lock50_exec=("lock50_exec_return", "mean"),
            lock50_same_close=("lock50_same_close_return", "mean"),
            picks=("symbol", "size"),
        )
    )

    bootstrap_rows = []
    rng = np.random.default_rng(seed)
    for strategy, frame in signal.groupby("strategy"):
        for variant in ("lock50_exec", "lock50_same_close"):
            diff = (frame[variant] - frame["month_end_exec"]).to_numpy(float)
            n = len(diff)
            require(n >= 20, f"too few paired signals {strategy}: {n}")
            sample_idx = rng.integers(0, n, size=(reps, n))
            means = diff[sample_idx].mean(axis=1)
            bootstrap_rows.append({
                "strategy": strategy,
                "variant": variant,
                "paired_signals": n,
                "baseline_mean": float(frame["month_end_exec"].mean()),
                "variant_mean": float(frame[variant].mean()),
                "mean_delta_vs_baseline": float(diff.mean()),
                "bootstrap_ci95_low": float(np.quantile(means, 0.025)),
                "bootstrap_ci95_high": float(np.quantile(means, 0.975)),
                "bootstrap_probability_delta_positive": float((means > 0).mean()),
                "bootstrap_reps": int(reps),
                "bootstrap_seed": int(seed),
            })
    bootstrap = pd.DataFrame(bootstrap_rows)

    diagnostic_rows = []
    for strategy, frame in trades.groupby("strategy"):
        plus20 = frame["mfe"] >= LOCK_ACTIVATION_GAIN
        diagnostic_rows.append({
            "strategy": strategy,
            "trades": int(len(frame)),
            "trigger_rate": float(frame["trigger_date"].notna().mean()),
            "mean_holding_days_exec": float((frame["lock50_exec_exit_date"] - frame["entry_date"]).dt.days.mean()),
            "median_holding_days_exec": float((frame["lock50_exec_exit_date"] - frame["entry_date"]).dt.days.median()),
            "mean_baseline_holding_days": float((frame["baseline_exit_date"] - frame["entry_date"]).dt.days.mean()),
            "round_trip_rate_given_plus20": float(((plus20) & (frame["baseline_return"] <= 0)).sum() / max(1, int(plus20.sum()))),
        })
    diagnostic = pd.DataFrame(diagnostic_rows)

    regime = (
        signal.groupby(["strategy", "regime"], as_index=False)
        .agg(
            signals=("signal_date", "size"),
            month_end_exec=("month_end_exec", "mean"),
            lock50_exec=("lock50_exec", "mean"),
            lock50_same_close=("lock50_same_close", "mean"),
        )
    )
    return signal, bootstrap, diagnostic, regime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=DEFAULT_REPS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    protocol = json.loads(Path(args.protocol).read_text(encoding="utf-8"))
    require(protocol["schema"] == "gate_btc.profit_retention_execution_protocol.v1_1", "unexpected v1.1 protocol")
    require(float(protocol["lock_activation_gain"]) == LOCK_ACTIVATION_GAIN, "activation threshold drift")
    require(float(protocol["lock_giveback_fraction"]) == LOCK_GIVEBACK_FRACTION, "giveback threshold drift")
    require(protocol["entry_selection"] == "UNCHANGED_FROM_PINNED_PHASE1_SELECTIONS_PIT", "entry-selection drift")

    manifest = json.loads((input_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    require(manifest["protocol"] == EXPECTED_PHASE1_PROTOCOL, "unexpected Phase-1 protocol")
    require(manifest["canonical_v2a_script_sha256"] == EXPECTED_CANONICAL_SHA, "frozen V2A SHA drift")
    require(manifest["history_pass_symbols"] == 444, "Phase-1 baseline drift")
    require(manifest["engine_feed"] is False and manifest["methodology_changes"] == 0, "Phase-1 safety drift")

    trades = build_trades(
        pd.read_csv(input_dir / "SELECTIONS_PIT.csv"),
        pd.read_csv(input_dir / "COVERAGE_BY_SIGNAL.csv"),
        pd.read_csv(input_dir / "CASCADE_DAILY_HISTORY.csv.gz"),
    )
    signal, bootstrap, diagnostic, regime = summarize(trades, args.bootstrap_reps, args.seed)
    require(trades["signal_date"].nunique() == 62, "complete signal count drift")
    require(len(trades) == 1240, "baseline trade count drift")

    trades.to_csv(output_dir / "EXECUTION_CONSISTENT_TRADES.csv.gz", index=False, compression="gzip")
    signal.to_csv(output_dir / "SIGNAL_EXECUTION_RETURNS.csv", index=False)
    bootstrap.to_csv(output_dir / "EXECUTION_BOOTSTRAP.csv", index=False)
    diagnostic.to_csv(output_dir / "EXECUTION_DIAGNOSTIC.csv", index=False)
    regime.to_csv(output_dir / "EXECUTION_BY_REGIME.csv", index=False)

    result = {
        "schema": "gate_btc.profit_retention_execution_audit.v1_1",
        "status": "PASS_RESEARCH_ONLY",
        "phase1_run_id": 31276127634,
        "complete_signal_months": 62,
        "baseline_trades": 1240,
        "entry_execution": "NEXT_DAILY_BAR",
        "lock_activation_gain": LOCK_ACTIVATION_GAIN,
        "lock_giveback_fraction": LOCK_GIVEBACK_FRACTION,
        "primary_variant": "LOCK50_EXECUTABLE_NEXT_BAR",
        "reference_variant": "LOCK50_SAME_CLOSE_WITH_NEXT_BAR_ENTRY",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changes_phase1": 0,
    }
    (output_dir / "PHASE2_V11_SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
