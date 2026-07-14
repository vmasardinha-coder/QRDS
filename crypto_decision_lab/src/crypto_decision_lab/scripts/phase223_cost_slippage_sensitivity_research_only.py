from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    monotonic_non_decreasing,
    phase_status,
    read_json,
    research_caps,
    write_json,
    write_markdown,
)


def cost_slippage_scenarios(
    assumed_turnover_events: int = 100,
) -> list[dict[str, Any]]:
    scenarios = []
    for transaction_cost_bps, slippage_bps in (
        (0, 0),
        (2, 1),
        (5, 3),
        (10, 5),
        (25, 10),
        (50, 25),
    ):
        total_bps_per_event = transaction_cost_bps + slippage_bps
        cumulative_burden = assumed_turnover_events * total_bps_per_event / 10_000.0
        scenarios.append(
            {
                "transaction_cost_bps": transaction_cost_bps,
                "slippage_bps": slippage_bps,
                "assumed_turnover_events": assumed_turnover_events,
                "cumulative_notional_cost_fraction": cumulative_burden,
            }
        )
    return scenarios


def build_phase223(
    phase222_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase222 = read_json(phase222_artifact)
    scenarios = cost_slippage_scenarios()
    burdens = [item["cumulative_notional_cost_fraction"] for item in scenarios]
    monotonic = monotonic_non_decreasing(burdens)
    passed = bool(
        phase222["calibration_diagnostic_passed"]
        and len(scenarios) >= 5
        and monotonic
    )

    payload = {
        "phase": 223,
        "status": phase_status(
            passed,
            "COST_SLIPPAGE_SENSITIVITY_READY_RESEARCH_ONLY",
        ),
        "cost_slippage_sensitivity_passed": passed,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "cost_burden_monotonic": monotonic,
        "pnl_or_trade_simulation_performed": False,
        "caps": research_caps(),
        "interpretation": (
            "The scenarios measure hypothetical cost burden against notional "
            "turnover only. No trade, PnL, recommendation or execution claim "
            "is produced."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 223 - Cost and Slippage Sensitivity",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Scenarios:** `{len(scenarios)}`",
                f"**Monotonic burden:** `{monotonic}`",
                "**PnL or trade simulation:** `False`",
                "",
                "The diagnostic is research-only notional cost sensitivity.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase222-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase223(
        args.phase222_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE223:", payload["status"])
    print("Scenarios:", payload["scenario_count"])
    return 0 if payload["cost_slippage_sensitivity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
