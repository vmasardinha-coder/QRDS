#!/usr/bin/env python3
"""Emit explicit PIT coverage diagnostics from definitive research artifacts.

Reporting-only sidecar. It never changes membership, selections, returns,
coverage gating, strategy parameters, or the frozen engine.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(output_dir: Path, threshold: float = 0.95) -> dict:
    selections_path = output_dir / "SELECTIONS_PIT.csv"
    daily_path = output_dir / "DAILY_BASKETS_STRICT.csv.gz"
    require(selections_path.is_file(), "SELECTIONS_PIT.csv missing")
    require(daily_path.is_file(), "DAILY_BASKETS_STRICT.csv.gz missing")

    selections = pd.read_csv(selections_path)
    require(
        {"signal_date", "strategy", "members_covered", "members_directional_total"}.issubset(selections.columns),
        "selection coverage columns missing",
    )
    # Membership coverage is strategy-independent. Assert both frozen strategy
    # rows agree, then retain one row per signal date for an auditable report.
    grouped = selections.groupby("signal_date", sort=True)
    rows = []
    for signal_date, frame in grouped:
        covered_values = sorted(set(pd.to_numeric(frame["members_covered"], errors="raise").astype(int)))
        total_values = sorted(set(pd.to_numeric(frame["members_directional_total"], errors="raise").astype(int)))
        require(len(covered_values) == 1 and len(total_values) == 1, f"strategy coverage mismatch at {signal_date}")
        covered, total = covered_values[0], total_values[0]
        require(total > 0 and 0 <= covered <= total, f"invalid coverage at {signal_date}")
        rows.append(
            {
                "signal_date": signal_date,
                "members_covered": covered,
                "members_directional_total": total,
                "coverage_ratio": covered / total,
                "gate_95": covered / total >= threshold,
            }
        )
    by_signal = pd.DataFrame(rows).sort_values("signal_date")
    by_signal.to_csv(output_dir / "COVERAGE_BY_SIGNAL.csv", index=False)

    daily = pd.read_csv(daily_path)
    require({"date", "coverage_ratio"}.issubset(daily.columns), "daily coverage columns missing")
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily["coverage_ratio"] = pd.to_numeric(daily["coverage_ratio"], errors="raise")
    weekly = (
        daily.set_index("date")["coverage_ratio"]
        .groupby(pd.Grouper(freq="W-FRI"))
        .min()
        .dropna()
    )

    ratios = by_signal["coverage_ratio"]
    payload = {
        "schema": "gate_btc.pit_coverage_report.v1",
        "status": "PASS_REPORT_ONLY",
        "threshold": threshold,
        "signals": int(len(by_signal)),
        "signal_coverage_min": float(ratios.min()) if len(ratios) else None,
        "signal_coverage_mean": float(ratios.mean()) if len(ratios) else None,
        "signal_coverage_max": float(ratios.max()) if len(ratios) else None,
        "signals_at_or_above_threshold": int((ratios >= threshold).sum()),
        "weeks_raw": int(len(weekly)),
        "weekly_min_coverage_min": float(weekly.min()) if len(weekly) else None,
        "weekly_min_coverage_mean": float(weekly.mean()) if len(weekly) else None,
        "weekly_min_coverage_max": float(weekly.max()) if len(weekly) else None,
        "weeks_at_or_above_threshold": int((weekly >= threshold).sum()),
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "engine_feed": False,
        "methodology_changes": 0,
    }
    (output_dir / "COVERAGE_SUMMARY.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.95)
    args = parser.parse_args()
    run(args.output_dir, args.threshold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
