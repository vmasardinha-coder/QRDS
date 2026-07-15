from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase304_nested_walk_forward_v2_research_only import (
    _metrics,
    _trades,
)
from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    quantile,
    read_csv_gz,
    read_json,
    to_float,
    validate_phase,
    write_json,
    write_phase_summary,
)


def _metric_from_trades(trades: list[dict[str, Any]]) -> dict[str, Any]:
    return _metrics(trades)


def build(
    phase302_path: Path,
    phase303_path: Path,
    phase304_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase302 = read_json(phase302_path)
    phase303 = read_json(phase303_path)
    phase304 = read_json(phase304_path)
    validate_phase(phase302, 302)
    validate_phase(phase303, 303)
    validate_phase(phase304, 304)

    rows = read_csv_gz(ROOT / phase302["matrix_path"])
    rows.sort(key=lambda row: int(row["open_time_ms"]))
    closes = [float(row["close"]) for row in rows]
    by_id = {item["hypothesis_id"]: item for item in phase303["hypotheses"]}

    cost_trade_sets: dict[int, list[dict[str, Any]]] = {10: [], 30: [], 50: []}
    liquidity_trade_sets: dict[str, list[dict[str, Any]]] = {
        "all_10bps": [],
        "exclude_bottom_25pct_quote_volume_10bps": [],
        "top_50pct_quote_volume_10bps": [],
    }
    fold_thresholds: list[dict[str, Any]] = []

    for fold in phase304["fold_results"]:
        selected_id = fold["selected_hypothesis_id"]
        hypothesis = by_id.get(selected_id)
        if hypothesis is None:
            raise RuntimeError(f"Selected hypothesis is absent from closed registry: {selected_id}")
        train_values = [
            value
            for row in rows[int(fold["train_start"]) : int(fold["train_end"]) + 1]
            if (value := to_float(row.get("quote_volume"))) is not None and value > 0
        ]
        if len(train_values) < 100:
            raise RuntimeError("Insufficient training liquidity observations for stress threshold.")
        q25 = quantile(train_values, 0.25)
        q50 = quantile(train_values, 0.50)
        fold_thresholds.append(
            {
                "fold": int(fold["fold"]),
                "selected_hypothesis_id": selected_id,
                "training_quote_volume_q25": q25,
                "training_quote_volume_q50": q50,
            }
        )

        for cost in cost_trade_sets:
            trades = _trades(
                hypothesis,
                rows,
                closes,
                int(fold["outer_start"]),
                int(fold["outer_end"]),
                cost,
            )
            cost_trade_sets[cost].extend(trades)
            if cost == 10:
                liquidity_trade_sets["all_10bps"].extend(trades)
                liquidity_trade_sets["exclude_bottom_25pct_quote_volume_10bps"].extend(
                    trade
                    for trade in trades
                    if float(rows[int(trade["entry_index"])]["quote_volume"]) >= q25
                )
                liquidity_trade_sets["top_50pct_quote_volume_10bps"].extend(
                    trade
                    for trade in trades
                    if float(rows[int(trade["entry_index"])]["quote_volume"]) >= q50
                )

    cost_metrics = {
        str(cost): _metric_from_trades(trades)
        for cost, trades in sorted(cost_trade_sets.items())
    }
    liquidity_metrics = {
        key: _metric_from_trades(trades)
        for key, trades in liquidity_trade_sets.items()
    }

    extreme_cost_liquidity_pass = (
        cost_metrics["30"]["trade_count"] >= 50
        and cost_metrics["50"]["trade_count"] >= 50
        and cost_metrics["30"]["lower_95_per_10000_brl"] > 0
        and cost_metrics["50"]["lower_95_per_10000_brl"] > 0
        and liquidity_metrics["exclude_bottom_25pct_quote_volume_10bps"]["trade_count"] >= 40
        and liquidity_metrics["exclude_bottom_25pct_quote_volume_10bps"]["lower_95_per_10000_brl"] > 0
        and liquidity_metrics["top_50pct_quote_volume_10bps"]["trade_count"] >= 25
        and liquidity_metrics["top_50pct_quote_volume_10bps"]["lower_95_per_10000_brl"] > 0
    )
    reasons: list[str] = []
    if cost_metrics["30"]["lower_95_per_10000_brl"] <= 0:
        reasons.append("LOWER_95_NOT_POSITIVE_AT_30_BPS")
    if cost_metrics["50"]["lower_95_per_10000_brl"] <= 0:
        reasons.append("LOWER_95_NOT_POSITIVE_AT_50_BPS")
    if liquidity_metrics["exclude_bottom_25pct_quote_volume_10bps"]["lower_95_per_10000_brl"] <= 0:
        reasons.append("LOWER_95_NOT_POSITIVE_AFTER_LOW_LIQUIDITY_EXCLUSION")
    if liquidity_metrics["top_50pct_quote_volume_10bps"]["lower_95_per_10000_brl"] <= 0:
        reasons.append("LOWER_95_NOT_POSITIVE_IN_TOP_HALF_LIQUIDITY")
    if min(cost_metrics["30"]["trade_count"], cost_metrics["50"]["trade_count"]) < 50:
        reasons.append("INSUFFICIENT_EXTREME_COST_TRADES")

    payload = base_payload(309, "EXTREME_COST_LIQUIDITY_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE309_EXTREME_COST_LIQUIDITY_AUDIT_READY_RESEARCH_ONLY",
            "phase302_artifact": phase302_path.relative_to(ROOT).as_posix(),
            "phase302_fingerprint": phase302.get("artifact_fingerprint"),
            "phase303_artifact": phase303_path.relative_to(ROOT).as_posix(),
            "phase303_fingerprint": phase303.get("artifact_fingerprint"),
            "phase304_artifact": phase304_path.relative_to(ROOT).as_posix(),
            "phase304_fingerprint": phase304.get("artifact_fingerprint"),
            "selection_reused_without_reselection": True,
            "new_hypotheses_added": 0,
            "training_only_liquidity_thresholds": True,
            "cost_stress_bps": [10, 30, 50],
            "cost_metrics": cost_metrics,
            "liquidity_metrics": liquidity_metrics,
            "fold_liquidity_thresholds": fold_thresholds,
            "extreme_cost_liquidity_pass": extreme_cost_liquidity_pass,
            "failure_reasons": reasons,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase309_extreme_cost_liquidity_audit.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase309_extreme_cost_liquidity_audit_summary.md",
        title="Phase 309 — Extreme Cost and Liquidity Audit",
        gate=payload["gate"],
        bullets=[
            "Phase 304 fold selections reused without reselection: `True`",
            "New hypotheses added: `0`",
            f"Lower 95% per R$10.000 at 30 bps: `{cost_metrics['30']['lower_95_per_10000_brl']:.2f}`",
            f"Lower 95% per R$10.000 at 50 bps: `{cost_metrics['50']['lower_95_per_10000_brl']:.2f}`",
            f"Lower 95% after excluding bottom liquidity quartile: `{liquidity_metrics['exclude_bottom_25pct_quote_volume_10bps']['lower_95_per_10000_brl']:.2f}`",
            f"Extreme cost/liquidity pass: `{extreme_cost_liquidity_pass}`",
            f"Failure reasons: `{', '.join(reasons) if reasons else 'NONE'}`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase302-artifact",
        type=Path,
        default=ROOT / "artifacts/phase302_controlled_feature_registry_v2_research_only/phase302_controlled_feature_registry_v2.json",
    )
    parser.add_argument(
        "--phase303-artifact",
        type=Path,
        default=ROOT / "artifacts/phase303_finite_hypothesis_registry_v2_research_only/phase303_finite_hypothesis_registry_v2.json",
    )
    parser.add_argument(
        "--phase304-artifact",
        type=Path,
        default=ROOT / "artifacts/phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase309_extreme_cost_liquidity_audit_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(
        args.phase302_artifact,
        args.phase303_artifact,
        args.phase304_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("30 bps lower 95 per R$10.000:", payload["cost_metrics"]["30"]["lower_95_per_10000_brl"])
    print("50 bps lower 95 per R$10.000:", payload["cost_metrics"]["50"]["lower_95_per_10000_brl"])
    print("Extreme cost/liquidity pass:", payload["extreme_cost_liquidity_pass"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
