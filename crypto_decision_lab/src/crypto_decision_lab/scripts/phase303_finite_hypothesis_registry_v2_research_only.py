from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    write_json,
    write_text,
)

EXPERIMENT_BUDGET = 24
ALPHA = 0.05
COST_BPS = (5, 10, 20)


def _hypothesis(
    hypothesis_id: str,
    family: str,
    signal: str,
    feature: str,
    lookback_hours: int,
    holding_hours: int,
    threshold: float,
    direction: str,
    filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis_id,
        "family": family,
        "signal": signal,
        "feature": feature,
        "lookback_hours": lookback_hours,
        "holding_hours": holding_hours,
        "threshold": threshold,
        "direction": direction,
        "filters": filters or [],
        "cost_bps_scenarios": list(COST_BPS),
        "registered_before_evaluation": True,
        "parameter_mutation_allowed": False,
        "execution_allowed": False,
    }


def registry() -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []

    for lookback in (3, 6, 12):
        for holding in (4, 8):
            hypotheses.append(
                _hypothesis(
                    f"MR_LB{lookback}_H{holding}_T005",
                    "MEAN_REVERSION",
                    "negative feature beyond threshold",
                    f"return_{lookback if lookback in (4, 24) else '4h' if lookback <= 6 else '24h'}",
                    lookback,
                    holding,
                    0.005,
                    "CONTRARIAN",
                )
            )

    for lookback in (4, 12, 24):
        for holding in (4, 8):
            hypotheses.append(
                _hypothesis(
                    f"MOM_LB{lookback}_H{holding}_T004",
                    "MOMENTUM",
                    "feature beyond threshold",
                    f"return_{lookback if lookback in (4, 24) else '24h'}",
                    lookback,
                    holding,
                    0.004,
                    "FOLLOW",
                )
            )

    for lookback, holding in ((24, 4), (24, 8), (168, 8), (168, 24)):
        hypotheses.append(
            _hypothesis(
                f"TREND_SMA{lookback}_H{holding}_T003",
                "TREND",
                "SMA distance beyond threshold",
                f"sma_distance_{lookback}h",
                lookback,
                holding,
                0.003,
                "FOLLOW",
            )
        )

    for holding in (4, 8, 12, 24):
        hypotheses.append(
            _hypothesis(
                f"FUNDING_CONTRA_H{holding}_T0001",
                "DERIVATIVES_CONTRARIAN",
                "funding mean beyond threshold",
                "funding_mean_3",
                24,
                holding,
                0.0001,
                "CONTRARIAN",
            )
        )

    for holding in (4, 8, 12, 24):
        hypotheses.append(
            _hypothesis(
                f"OI_MOM_H{holding}_T005",
                "DERIVATIVES_MOMENTUM",
                "open-interest change and price agree",
                "open_interest_change_24h",
                24,
                holding,
                0.005,
                "FOLLOW",
                filters=[{"feature": "return_24h", "threshold": 0.0, "relation": "SAME_SIGN"}],
            )
        )

    if len(hypotheses) != EXPERIMENT_BUDGET:
        raise AssertionError(f"Registry size {len(hypotheses)} != budget {EXPERIMENT_BUDGET}")
    ids = [item["hypothesis_id"] for item in hypotheses]
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate hypothesis IDs.")
    return hypotheses


def build(phase302_path: Path, output_dir: Path) -> dict[str, Any]:
    phase302 = read_json(phase302_path)
    if phase302.get("phase") != 302:
        raise RuntimeError("Phase 302 artifact is invalid.")
    hypotheses = registry()
    payload = base_payload(303, "FINITE_HYPOTHESIS_REGISTRY_V2_CLOSED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE303_FINITE_HYPOTHESIS_REGISTRY_V2_READY_RESEARCH_ONLY",
            "phase302_artifact": phase302_path.relative_to(ROOT).as_posix(),
            "phase302_fingerprint": phase302["artifact_fingerprint"],
            "experiment_budget": EXPERIMENT_BUDGET,
            "registered_hypotheses": len(hypotheses),
            "budget_exhaustion_policy": "STOP_NO_EXTENSION",
            "registry_closed": True,
            "post_result_parameter_changes_allowed": False,
            "multiple_testing": {
                "method": "HOLM_BONFERRONI",
                "family_wise_alpha": ALPHA,
                "penalty_mandatory": True,
            },
            "cost_bps_scenarios": list(COST_BPS),
            "hypotheses": hypotheses,
            "strategy_approved": False,
            "historical_success_can_promote": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase303_finite_hypothesis_registry_v2.json", payload)
    write_text(
        ROOT / "docs/reports/evidence_v2/phase303_finite_hypothesis_registry_v2_summary.md",
        f"""# Phase 303 — Finite Hypothesis Registry v2

Gate: `{payload["gate"]}`

- Hard experiment budget: `{EXPERIMENT_BUDGET}`
- Registered hypotheses: `{len(hypotheses)}`
- Registry closed before evaluation: `True`
- Budget extension after bad results: `False`
- Multiple-testing method: `HOLM_BONFERRONI`
- Family-wise alpha: `{ALPHA}`
- Cost scenarios: `{", ".join(str(value) + " bps" for value in COST_BPS)}`
- Historical success can promote: `False`
- Strategy approved: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`

The registry prevents unlimited searching for a lucky result. A positive
historical result remains descriptive and cannot unlock forward, paper or real
execution.
""",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase302-artifact",
        type=Path,
        default=ROOT
        / "artifacts/phase302_controlled_feature_registry_v2_research_only/"
        "phase302_controlled_feature_registry_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase303_finite_hypothesis_registry_v2_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase302_artifact, args.output_dir)
    print(payload["gate"])
    print("Experiment budget:", payload["experiment_budget"])
    print("Registered hypotheses:", payload["registered_hypotheses"])
    print("Registry closed:", payload["registry_closed"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
