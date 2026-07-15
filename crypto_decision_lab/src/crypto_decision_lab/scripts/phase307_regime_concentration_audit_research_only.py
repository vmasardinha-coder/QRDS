from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def build(phase304_path: Path, output_dir: Path) -> dict[str, Any]:
    phase304 = read_json(phase304_path)
    validate_phase(phase304, 304)
    regimes = phase304.get("regime_robustness", {})
    if not isinstance(regimes, dict) or not regimes:
        raise RuntimeError("Phase 304 has no regime robustness evidence.")

    rows: list[dict[str, Any]] = []
    total_trades = sum(int(item.get("trade_count", item.get("count", 0))) for item in regimes.values())
    total_abs_contribution = 0.0
    raw_contributions: dict[str, float] = {}
    for regime, metrics in sorted(regimes.items()):
        trades = int(metrics.get("trade_count", metrics.get("count", 0)))
        mean_brl = float(metrics.get("mean_per_10000_brl", 0.0))
        lower_brl = float(metrics.get("lower_95_per_10000_brl", 0.0))
        contribution = mean_brl * trades
        raw_contributions[regime] = contribution
        total_abs_contribution += abs(contribution)
        rows.append(
            {
                "regime": regime,
                "trade_count": trades,
                "trade_share": trades / total_trades if total_trades else 0.0,
                "mean_per_10000_brl": mean_brl,
                "lower_95_per_10000_brl": lower_brl,
                "contribution_proxy_brl": contribution,
            }
        )
    for row in rows:
        row["absolute_contribution_share"] = (
            abs(float(row["contribution_proxy_brl"])) / total_abs_contribution
            if total_abs_contribution
            else 0.0
        )

    max_trade_share = max(float(row["trade_share"]) for row in rows)
    max_contribution_share = max(float(row["absolute_contribution_share"]) for row in rows)
    minimum_regime_trades = min(int(row["trade_count"]) for row in rows)
    positive_mean_count = sum(float(row["mean_per_10000_brl"]) > 0 for row in rows)
    positive_lower_count = sum(float(row["lower_95_per_10000_brl"]) > 0 for row in rows)

    regime_concentration_pass = (
        len(rows) >= 3
        and minimum_regime_trades >= 10
        and max_trade_share <= 0.70
        and max_contribution_share <= 0.80
        and positive_mean_count == len(rows)
        and positive_lower_count == len(rows)
    )
    reasons: list[str] = []
    if len(rows) < 3:
        reasons.append("FEWER_THAN_THREE_REGIMES")
    if minimum_regime_trades < 10:
        reasons.append("REGIME_WITH_TOO_FEW_TRADES")
    if max_trade_share > 0.70:
        reasons.append("TRADE_COUNT_CONCENTRATED_IN_ONE_REGIME")
    if max_contribution_share > 0.80:
        reasons.append("PERFORMANCE_CONCENTRATED_IN_ONE_REGIME")
    if positive_mean_count != len(rows):
        reasons.append("AT_LEAST_ONE_REGIME_HAS_NON_POSITIVE_MEAN")
    if positive_lower_count != len(rows):
        reasons.append("AT_LEAST_ONE_REGIME_HAS_NON_POSITIVE_LOWER_95")

    payload = base_payload(307, "REGIME_CONCENTRATION_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE307_REGIME_CONCENTRATION_AUDIT_READY_RESEARCH_ONLY",
            "phase304_artifact": phase304_path.relative_to(ROOT).as_posix(),
            "phase304_fingerprint": phase304.get("artifact_fingerprint"),
            "regime_count": len(rows),
            "total_trade_count": total_trades,
            "regimes": rows,
            "max_trade_share": max_trade_share,
            "max_absolute_contribution_share": max_contribution_share,
            "minimum_regime_trade_count": minimum_regime_trades,
            "positive_mean_regime_count": positive_mean_count,
            "positive_lower_95_regime_count": positive_lower_count,
            "regime_concentration_pass": regime_concentration_pass,
            "failure_reasons": reasons,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase307_regime_concentration_audit.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase307_regime_concentration_audit_summary.md",
        title="Phase 307 — Regime Concentration Audit",
        gate=payload["gate"],
        bullets=[
            f"Regimes evaluated: `{len(rows)}`",
            f"Total modeled trades: `{total_trades}`",
            f"Largest trade-count share: `{max_trade_share:.2%}`",
            f"Largest absolute contribution share: `{max_contribution_share:.2%}`",
            f"Regimes with positive mean: `{positive_mean_count}/{len(rows)}`",
            f"Regimes with positive lower 95%: `{positive_lower_count}/{len(rows)}`",
            f"Regime concentration pass: `{regime_concentration_pass}`",
            f"Failure reasons: `{', '.join(reasons) if reasons else 'NONE'}`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase304-artifact",
        type=Path,
        default=ROOT / "artifacts/phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase307_regime_concentration_audit_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase304_artifact, args.output_dir)
    print(payload["gate"])
    print("Regimes:", payload["regime_count"])
    print("Total trades:", payload["total_trade_count"])
    print("Max trade share:", payload["max_trade_share"])
    print("Regime concentration pass:", payload["regime_concentration_pass"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
