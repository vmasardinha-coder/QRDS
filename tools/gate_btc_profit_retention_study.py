#!/usr/bin/env python3
"""GATE BTC Phase 2: profit-retention / holding-time study.

Research-only sidecar. It NEVER changes entry selection. It consumes a pinned
Phase-1 point-in-time survivorship artifact and compares predeclared exit rules
on the exact selected altcoin picks from QOS Moderada and Ultra.

Primary sample: signal months with Phase-1 PIT coverage >=95% and a complete
next monthly rebalance boundary. Prices are daily closes from the already
validated Phase-1 cascade. All policies are evaluated from the same entry
anchor (signal-date close) and never use future information before their exit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

POLICIES = (
    "MONTH_END",
    "FIXED_7D",
    "FIXED_14D",
    "FIXED_21D",
    "LOCK_25",
    "LOCK_50",
    "LOCK_75",
)
LOCK_ACTIVATION_GAIN = 0.20
BOOTSTRAP_SEED = 20260808
DEFAULT_BOOTSTRAP_REPS = 10_000
PHASE1_EXPECTED_PROTOCOL = "EXTERNAL_MONTHLY_PIT_TOP150_STRICT_NEXT_BAR"
PHASE1_EXPECTED_CANONICAL_SHA = "6eea7a1b8caef7ff19188ab32f32f2e1a26eef1a06027764b720b3d351e9e804"


def safety() -> dict:
    return {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "strategy_inputs_changed": False,
        "entry_selection_changed": False,
        "methodology_changes_phase1": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def policy_exit(prices: pd.Series, signal_date: pd.Timestamp, boundary: pd.Timestamp, policy: str) -> tuple[pd.Timestamp, float]:
    """Return (exit_date, return) using only closes observed up to the exit."""
    prices = prices.sort_index().astype(float)
    require(signal_date in prices.index, f"missing entry close {signal_date.date()}")
    require(boundary in prices.index, f"missing boundary close {boundary.date()}")
    entry = float(prices.loc[signal_date])
    forward = prices[(prices.index > signal_date) & (prices.index <= boundary)]
    require(not forward.empty, "empty forward window")

    if policy == "MONTH_END":
        return boundary, float(prices.loc[boundary] / entry - 1.0)

    if policy.startswith("FIXED_"):
        days = int(policy.split("_")[1][:-1])
        target = signal_date + pd.Timedelta(days=days)
        eligible = forward[forward.index >= target]
        if eligible.empty:
            exit_date = forward.index[-1]
            exit_price = float(forward.iloc[-1])
        else:
            exit_date = eligible.index[0]
            exit_price = float(eligible.iloc[0])
        return pd.Timestamp(exit_date), exit_price / entry - 1.0

    if policy.startswith("LOCK_"):
        giveback_fraction = float(policy.split("_")[1]) / 100.0
        peak_gain = float("-inf")
        activated = False
        for date, price in forward.items():
            ret = float(price / entry - 1.0)
            peak_gain = max(peak_gain, ret)
            if peak_gain >= LOCK_ACTIVATION_GAIN:
                activated = True
            # Giveback is measured on PROFIT, not price: LOCK_50 exits when
            # current gain falls to <=50% of the best gain after activation.
            if activated and ret <= peak_gain * (1.0 - giveback_fraction):
                return pd.Timestamp(date), ret
        return boundary, float(prices.loc[boundary] / entry - 1.0)

    raise ValueError(f"unknown policy {policy}")


def build_trades(selections: pd.DataFrame, coverage: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    selections = selections.copy()
    selections["signal_date"] = pd.to_datetime(selections["signal_date"])
    coverage = coverage.copy()
    coverage["signal_date"] = pd.to_datetime(coverage["signal_date"])
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])

    selections = selections.merge(coverage[["signal_date", "coverage_ratio", "gate_95"]], on="signal_date", how="left", validate="many_to_one")
    require(selections["gate_95"].notna().all(), "selection/coverage calendar mismatch")
    eligible = selections[selections["gate_95"].astype(bool)].copy()

    all_signal_dates = sorted(selections["signal_date"].unique())
    next_signal = {pd.Timestamp(all_signal_dates[i]): pd.Timestamp(all_signal_dates[i + 1]) for i in range(len(all_signal_dates) - 1)}
    prices = {
        symbol: frame.sort_values("date").drop_duplicates("date", keep="last").set_index("date")["close_usd"].astype(float)
        for symbol, frame in history.groupby("symbol")
    }

    rows = []
    for record in eligible.itertuples(index=False):
        signal_date = pd.Timestamp(record.signal_date)
        if signal_date not in next_signal:
            # Last signal has no complete monthly forward boundary: fail closed
            # from the primary analysis instead of shortening its holding window.
            continue
        boundary = next_signal[signal_date]
        picks = [x for x in str(record.picks or "").split(";") if x and x != "nan"]
        require(picks, f"empty picks {signal_date.date()} {record.strategy}")
        for symbol in picks:
            require(symbol in prices, f"missing selected symbol history {symbol}")
            series = prices[symbol]
            require(signal_date in series.index, f"missing {symbol} entry on {signal_date.date()}")
            require(boundary in series.index, f"missing {symbol} boundary on {boundary.date()}")
            entry = float(series.loc[signal_date])
            window = series[(series.index >= signal_date) & (series.index <= boundary)]
            path_returns = window / entry - 1.0
            mfe = float(path_returns.max())
            mae = float(path_returns.min())
            baseline = float(series.loc[boundary] / entry - 1.0)
            for policy in POLICIES:
                exit_date, policy_return = policy_exit(series, signal_date, boundary, policy)
                rows.append({
                    "signal_date": signal_date,
                    "boundary_date": boundary,
                    "strategy": record.strategy,
                    "regime": record.regime,
                    "symbol": symbol,
                    "coverage_ratio": float(record.coverage_ratio),
                    "policy": policy,
                    "exit_date": exit_date,
                    "holding_days": int((exit_date - signal_date).days),
                    "return": float(policy_return),
                    "month_end_return": baseline,
                    "mfe": mfe,
                    "mae": mae,
                })
    trades = pd.DataFrame(rows)
    require(not trades.empty, "no Phase-2 trades")
    require(set(trades["policy"]) == set(POLICIES), "policy set mismatch")
    return trades


def paired_bootstrap(signal_policy: pd.DataFrame, reps: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for strategy in sorted(signal_policy["strategy"].unique()):
        pivot = signal_policy[signal_policy["strategy"] == strategy].pivot(index="signal_date", columns="policy", values="sleeve_return").dropna()
        require("MONTH_END" in pivot.columns, f"missing baseline {strategy}")
        n = len(pivot)
        require(n >= 20, f"too few paired signals {strategy}: {n}")
        for policy in POLICIES:
            if policy == "MONTH_END":
                continue
            diff = (pivot[policy] - pivot["MONTH_END"]).to_numpy(float)
            sample_idx = rng.integers(0, n, size=(reps, n))
            boot_means = diff[sample_idx].mean(axis=1)
            rows.append({
                "strategy": strategy,
                "policy": policy,
                "paired_signals": n,
                "mean_delta_vs_month_end": float(diff.mean()),
                "bootstrap_ci95_low": float(np.quantile(boot_means, 0.025)),
                "bootstrap_ci95_high": float(np.quantile(boot_means, 0.975)),
                "bootstrap_probability_delta_positive": float((boot_means > 0).mean()),
                "bootstrap_reps": int(reps),
                "bootstrap_seed": int(seed),
            })
    return pd.DataFrame(rows)


def summarize(trades: pd.DataFrame, reps: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    signal_policy = (
        trades.groupby(["signal_date", "strategy", "regime", "policy"], as_index=False)
        .agg(sleeve_return=("return", "mean"), picks=("symbol", "size"))
    )
    summary = (
        signal_policy.groupby(["strategy", "policy"], as_index=False)
        .agg(
            signals=("signal_date", "size"),
            mean_sleeve_return=("sleeve_return", "mean"),
            median_sleeve_return=("sleeve_return", "median"),
            win_rate=("sleeve_return", lambda x: float((x > 0).mean())),
            p10=("sleeve_return", lambda x: float(np.quantile(x, 0.10))),
            p90=("sleeve_return", lambda x: float(np.quantile(x, 0.90))),
        )
    )
    baseline_mean = summary[summary["policy"] == "MONTH_END"].set_index("strategy")["mean_sleeve_return"]
    summary["mean_delta_vs_month_end"] = summary.apply(lambda r: float(r.mean_sleeve_return - baseline_mean.loc[r.strategy]), axis=1)

    regime = (
        signal_policy.groupby(["strategy", "regime", "policy"], as_index=False)
        .agg(signals=("signal_date", "size"), mean_sleeve_return=("sleeve_return", "mean"))
    )
    bootstrap = paired_bootstrap(signal_policy, reps=reps, seed=seed)

    baseline = trades[trades["policy"] == "MONTH_END"].copy()
    baseline["giveback"] = baseline["mfe"] - baseline["return"]
    baseline["round_trip"] = (baseline["mfe"] >= LOCK_ACTIVATION_GAIN) & (baseline["return"] <= 0)
    baseline["positive_capture"] = np.where(
        baseline["mfe"] > 0,
        np.maximum(baseline["return"], 0.0) / baseline["mfe"],
        np.nan,
    )
    diagnostic = {}
    for strategy, frame in baseline.groupby("strategy"):
        hit = frame[frame["mfe"] >= LOCK_ACTIVATION_GAIN]
        diagnostic[strategy] = {
            "trades": int(len(frame)),
            "mean_month_end_return": float(frame["return"].mean()),
            "median_month_end_return": float(frame["return"].median()),
            "mean_mfe": float(frame["mfe"].mean()),
            "median_mfe": float(frame["mfe"].median()),
            "mean_giveback": float(frame["giveback"].mean()),
            "median_giveback": float(frame["giveback"].median()),
            "median_positive_profit_capture": float(frame["positive_capture"].median(skipna=True)),
            "hit_plus20_rate": float((frame["mfe"] >= LOCK_ACTIVATION_GAIN).mean()),
            "round_trip_rate_all_trades": float(frame["round_trip"].mean()),
            "round_trip_rate_given_plus20": float((hit["return"] <= 0).mean()) if len(hit) else None,
            "mean_mfe_given_plus20": float(hit["mfe"].mean()) if len(hit) else None,
            "mean_month_end_return_given_plus20": float(hit["return"].mean()) if len(hit) else None,
        }
    return signal_policy, summary, regime, bootstrap, diagnostic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=DEFAULT_BOOTSTRAP_REPS)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--phase1-run-id", type=int, default=31276127634)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((input_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    require(manifest["protocol"] == PHASE1_EXPECTED_PROTOCOL, "unexpected Phase-1 protocol")
    require(manifest["canonical_v2a_script_sha256"] == PHASE1_EXPECTED_CANONICAL_SHA, "unexpected frozen V2A SHA")
    require(manifest["cmc_snapshots"] == 74, "unexpected PIT snapshot count")
    require(manifest["history_pass_symbols"] == 444, "Phase-1 baseline drift")
    require(manifest["methodology_changes"] == 0 and manifest["engine_feed"] is False, "Phase-1 safety drift")

    selections = pd.read_csv(input_dir / "SELECTIONS_PIT.csv")
    coverage = pd.read_csv(input_dir / "COVERAGE_BY_SIGNAL.csv")
    history = pd.read_csv(input_dir / "CASCADE_DAILY_HISTORY.csv.gz")
    trades = build_trades(selections, coverage, history)
    signal_policy, summary, regime, bootstrap, diagnostic = summarize(trades, args.bootstrap_reps, args.seed)

    baseline_trades = trades[trades["policy"] == "MONTH_END"]
    eligible_signals = int(baseline_trades["signal_date"].nunique())
    require(eligible_signals >= 50, f"too few complete >=95% signals: {eligible_signals}")

    trades.to_csv(output_dir / "PROFIT_RETENTION_TRADES.csv.gz", index=False, compression="gzip")
    signal_policy.to_csv(output_dir / "SIGNAL_POLICY_RETURNS.csv", index=False)
    summary.to_csv(output_dir / "POLICY_SUMMARY.csv", index=False)
    regime.to_csv(output_dir / "POLICY_BY_REGIME.csv", index=False)
    bootstrap.to_csv(output_dir / "PAIRED_BOOTSTRAP.csv", index=False)
    (output_dir / "BASELINE_GIVEBACK_DIAGNOSTIC.json").write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "schema": "gate_btc.profit_retention_phase2.v1",
        "status": "PASS_RESEARCH_ONLY",
        "phase1_run_id": int(args.phase1_run_id),
        "phase1_protocol": manifest["protocol"],
        "phase1_history_pass_symbols": manifest["history_pass_symbols"],
        "sample_rule": "SIGNAL_COVERAGE_GE_95_AND_COMPLETE_NEXT_MONTH_BOUNDARY",
        "complete_signal_months": eligible_signals,
        "baseline_trades": int(len(baseline_trades)),
        "policies": list(POLICIES),
        "lock_activation_gain": LOCK_ACTIVATION_GAIN,
        "lock_definition": "exit when current unrealized gain <= peak_gain*(1-giveback_fraction), after peak_gain>=20%; no pre-activation stop-loss",
        "fixed_horizon_definition": "first available daily close on/after N calendar days after signal; never beyond next monthly boundary",
        "bootstrap_reps": int(args.bootstrap_reps),
        "bootstrap_seed": int(args.seed),
        "primary_metric": "paired mean selected-alt-sleeve return delta versus MONTH_END by signal month",
        "diagnostic": diagnostic,
        **safety(),
    }
    (output_dir / "PHASE2_SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
