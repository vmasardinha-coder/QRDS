from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    derived_price_views,
    locks_copy,
    mean,
    percentile,
    phase_status,
    read_json,
    read_jsonl,
    relative_dispersion,
    research_caps,
    write_json,
    write_markdown,
)


def diagnose_agreement(rows: list[dict[str, Any]], threshold: float = 0.10) -> dict[str, Any]:
    dispersions = [
        relative_dispersion(derived_price_views(row).values())
        for row in rows
    ]
    agreement_flags = [value <= threshold for value in dispersions]
    return {
        "view_names": ["close", "hlc3", "ohlc4"],
        "view_count": 3,
        "independent_source_count": 0,
        "row_count": len(rows),
        "dispersion_threshold": threshold,
        "agreement_ratio": mean(1.0 if flag else 0.0 for flag in agreement_flags),
        "mean_relative_dispersion": mean(dispersions),
        "p95_relative_dispersion": percentile(dispersions, 0.95),
        "maximum_relative_dispersion": max(dispersions) if dispersions else 0.0,
    }


def build_phase217(
    phase216_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase216 = read_json(phase216_artifact)
    rows = read_jsonl(dataset_path)
    diagnostic = diagnose_agreement(rows)
    passed = bool(
        phase216["provenance_completeness_passed"]
        and diagnostic["row_count"] > 0
        and diagnostic["view_count"] == 3
        and 0.0 <= diagnostic["agreement_ratio"] <= 1.0
        and diagnostic["maximum_relative_dispersion"] >= 0.0
    )

    payload = {
        "phase": 217,
        "status": phase_status(
            passed,
            "MULTI_VIEW_AGREEMENT_DIAGNOSTICS_READY_RESEARCH_ONLY",
        ),
        "multi_source_agreement_diagnostic_passed": passed,
        "diagnostic_mode": "DERIVED_OHLC_VIEWS_NOT_INDEPENDENT_SOURCES",
        "diagnostic": diagnostic,
        "independent_source_agreement_validated": False,
        "caps": research_caps(),
        "interpretation": (
            "The diagnostic compares internally derived OHLC views. It is a "
            "consistency check, not evidence that independent exchanges or "
            "vendors agree and not a data-trust approval."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 217 - Multi-Source Agreement Diagnostics",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Mode:** `{payload['diagnostic_mode']}`",
                f"**Agreement ratio:** `{diagnostic['agreement_ratio']:.6f}`",
                f"**Independent sources:** `{diagnostic['independent_source_count']}`",
                "",
                "The views are derived from the same OHLC row. Independent "
                "source agreement remains explicitly unvalidated.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase216-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase217(
        args.phase216_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE217:", payload["status"])
    print("Agreement ratio:", payload["diagnostic"]["agreement_ratio"])
    print("Independent source agreement validated: False")
    return 0 if payload["multi_source_agreement_diagnostic_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
