from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    mean,
    percentile,
    read_json,
    write_json,
    write_markdown,
)


def build_phase213(
    phase209_artifact: Path,
    phase212_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase209 = read_json(phase209_artifact)
    phase212 = read_json(phase212_artifact)
    results = phase209["results"]
    volatilities = [
        float(item["realized_volatility"])
        for item in results
    ]
    lower = percentile(volatilities, 1.0 / 3.0)
    upper = percentile(volatilities, 2.0 / 3.0)

    regimes: dict[str, list[dict[str, Any]]] = {
        "LOW_VOLATILITY": [],
        "MID_VOLATILITY": [],
        "HIGH_VOLATILITY": [],
    }

    ranked = sorted(
        results,
        key=lambda item: (
            float(item["realized_volatility"]),
            str(item.get("symbol", "")),
            int(item.get("window_index", 0)),
        ),
    )
    total = len(ranked)
    for rank, item in enumerate(ranked):
        fraction = rank / max(total, 1)
        if fraction < 1.0 / 3.0:
            regime = "LOW_VOLATILITY"
        elif fraction < 2.0 / 3.0:
            regime = "MID_VOLATILITY"
        else:
            regime = "HIGH_VOLATILITY"
        regimes[regime].append(item)

    regime_summary = {}
    for regime, items in regimes.items():
        regime_summary[regime] = {
            "window_count": len(items),
            "mean_normalized_mae": round(
                mean(float(item["normalized_mae"]) for item in items),
                12,
            ),
            "mean_directional_agreement": round(
                mean(
                    float(item["directional_agreement"])
                    for item in items
                ),
                12,
            ),
        }

    covered_regimes = sum(
        1
        for item in regime_summary.values()
        if item["window_count"] > 0
    )
    audit_passed = bool(
        phase209["historical_replay_passed"]
        and phase212["stability_audit_passed"]
        and len(results) >= 2
        and covered_regimes >= 2
    )

    payload = {
        "phase": 213,
        "status": (
            "REGIME_SEGMENTATION_AUDIT_READY_RESEARCH_ONLY"
            if audit_passed
            else "NEEDS_REVIEW"
        ),
        "regime_segmentation_passed": audit_passed,
        "thresholds": {
            "lower_volatility_quantile": round(lower, 12),
            "upper_volatility_quantile": round(upper, 12),
        },
        "covered_regimes": covered_regimes,
        "regimes": regime_summary,
        "interpretation": (
            "Regime segmentation is descriptive. Differences between "
            "regimes do not constitute a signal, recommendation or edge."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    lines = [
        "# Phase 213 - Regime Segmentation Audit",
        "",
        f"**Status:** `{payload['status']}`",
        f"**Covered regimes:** `{covered_regimes}`",
        "",
        "| Regime | Windows | Mean normalized MAE |",
        "|---|---:|---:|",
    ]
    for regime, item in regime_summary.items():
        lines.append(
            f"| {regime} | {item['window_count']} | "
            f"{item['mean_normalized_mae']} |"
        )
    lines.extend(
        [
            "",
            "The regime table is descriptive and does not create "
            "market actions.",
        ]
    )
    write_markdown(documentation_path, "\n".join(lines))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase212-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase213(
        args.phase209_artifact,
        args.phase212_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE213:", payload["status"])
    print("Covered regimes:", payload["covered_regimes"])
    return 0 if payload["regime_segmentation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
