from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase304_nested_walk_forward_v2_research_only import (
    _metrics,
    _signal,
)
from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_csv_gz,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def _delayed_trades(
    hypothesis: dict[str, Any],
    rows: list[dict[str, str]],
    closes: list[float],
    start: int,
    end: int,
    *,
    delay_hours: int,
    cost_bps: int = 10,
) -> list[dict[str, Any]]:
    holding = int(hypothesis["holding_hours"])
    cost = cost_bps / 10000.0
    output: list[dict[str, Any]] = []
    index = max(start, 168)
    final_signal = min(end, len(rows) - delay_hours - holding - 1)
    while index <= final_signal:
        direction = _signal(hypothesis, index, rows, closes)
        if direction == 0:
            index += 1
            continue
        entry_index = index + delay_hours
        exit_index = entry_index + holding
        gross = direction * (closes[exit_index] / closes[entry_index] - 1.0)
        output.append(
            {
                "signal_index": index,
                "entry_index": entry_index,
                "exit_index": exit_index,
                "signal_time_ms": int(rows[index]["open_time_ms"]),
                "entry_time_ms": int(rows[entry_index]["open_time_ms"]),
                "direction": direction,
                "gross_return": gross,
                "net_return": gross - cost,
                "delay_hours": delay_hours,
            }
        )
        index += holding
    return output


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

    delay_sets: dict[int, list[dict[str, Any]]] = {0: [], 1: [], 2: []}
    for fold in phase304["fold_results"]:
        selected_id = fold["selected_hypothesis_id"]
        hypothesis = by_id.get(selected_id)
        if hypothesis is None:
            raise RuntimeError(f"Selected hypothesis is absent from closed registry: {selected_id}")
        for delay in delay_sets:
            delay_sets[delay].extend(
                _delayed_trades(
                    hypothesis,
                    rows,
                    closes,
                    int(fold["outer_start"]),
                    int(fold["outer_end"]),
                    delay_hours=delay,
                    cost_bps=10,
                )
            )

    delay_metrics = {
        str(delay): _metrics(trades)
        for delay, trades in sorted(delay_sets.items())
    }
    baseline_mean = float(delay_metrics["0"]["mean_per_10000_brl"])
    delayed_means = [
        float(delay_metrics[str(delay)]["mean_per_10000_brl"])
        for delay in (1, 2)
    ]
    worst_delayed_mean = min(delayed_means)
    if baseline_mean > 0:
        relative_decay = max(0.0, (baseline_mean - worst_delayed_mean) / baseline_mean)
    elif baseline_mean < 0:
        relative_decay = max(0.0, (abs(worst_delayed_mean) - abs(baseline_mean)) / abs(baseline_mean))
    else:
        relative_decay = 1.0 if worst_delayed_mean != 0 else 0.0

    timestamp_sensitivity_pass = (
        all(delay_metrics[str(delay)]["trade_count"] >= 50 for delay in (0, 1, 2))
        and all(delay_metrics[str(delay)]["lower_95_per_10000_brl"] > 0 for delay in (0, 1, 2))
        and relative_decay <= 0.50
    )
    reasons: list[str] = []
    for delay in (0, 1, 2):
        if delay_metrics[str(delay)]["lower_95_per_10000_brl"] <= 0:
            reasons.append(f"LOWER_95_NOT_POSITIVE_AT_DELAY_{delay}H")
    if min(delay_metrics[str(delay)]["trade_count"] for delay in (0, 1, 2)) < 50:
        reasons.append("INSUFFICIENT_DELAY_STRESS_TRADES")
    if relative_decay > 0.50:
        reasons.append("RESULT_DECAYS_MORE_THAN_50_PERCENT_WITH_DELAY")

    payload = base_payload(310, "TIMESTAMP_SENSITIVITY_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE310_TIMESTAMP_SENSITIVITY_AUDIT_READY_RESEARCH_ONLY",
            "phase302_artifact": phase302_path.relative_to(ROOT).as_posix(),
            "phase302_fingerprint": phase302.get("artifact_fingerprint"),
            "phase303_artifact": phase303_path.relative_to(ROOT).as_posix(),
            "phase303_fingerprint": phase303.get("artifact_fingerprint"),
            "phase304_artifact": phase304_path.relative_to(ROOT).as_posix(),
            "phase304_fingerprint": phase304.get("artifact_fingerprint"),
            "selection_reused_without_reselection": True,
            "future_data_used_for_signal": False,
            "entry_delay_hours_tested": [0, 1, 2],
            "cost_bps": 10,
            "delay_metrics": delay_metrics,
            "worst_delayed_mean_per_10000_brl": worst_delayed_mean,
            "relative_decay_vs_zero_delay": relative_decay,
            "timestamp_sensitivity_pass": timestamp_sensitivity_pass,
            "failure_reasons": reasons,
            "new_hypotheses_added": 0,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase310_timestamp_sensitivity_audit.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase310_timestamp_sensitivity_audit_summary.md",
        title="Phase 310 — Timestamp Sensitivity Audit",
        gate=payload["gate"],
        bullets=[
            "Phase 304 fold selections reused without reselection: `True`",
            "Future data used to create signal: `False`",
            "Entry delays tested: `0h, 1h, 2h`",
            f"Zero-delay mean per R$10.000: `{delay_metrics['0']['mean_per_10000_brl']:.2f}`",
            f"One-hour delay mean per R$10.000: `{delay_metrics['1']['mean_per_10000_brl']:.2f}`",
            f"Two-hour delay mean per R$10.000: `{delay_metrics['2']['mean_per_10000_brl']:.2f}`",
            f"Timestamp sensitivity pass: `{timestamp_sensitivity_pass}`",
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
        default=ROOT / "artifacts/phase310_timestamp_sensitivity_audit_research_only",
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
    print("Delays tested:", ", ".join(str(value) for value in payload["entry_delay_hours_tested"]))
    print("Timestamp sensitivity pass:", payload["timestamp_sensitivity_pass"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
