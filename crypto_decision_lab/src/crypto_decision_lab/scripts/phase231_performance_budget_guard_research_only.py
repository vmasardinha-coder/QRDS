from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Callable

from crypto_decision_lab.scripts.phase174_shadow_readiness_preflight_research_only import (
    build_shadow_readiness_preflight,
)
from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    clear_registry_caches,
    project_root,
    write_json,
    write_markdown,
)


def measure(
    function: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    payload = function()
    return payload, time.perf_counter() - started


def build_performance_budget_guard(
    root: Path | None = None,
    *,
    clocked_builder: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    clear_registry_caches()
    builder = (
        clocked_builder
        if clocked_builder is not None
        else lambda: build_shadow_readiness_preflight(resolved)
    )
    cold_payload, cold_seconds = measure(builder)
    warm_payload, warm_seconds = measure(builder)

    absolute_budget_seconds = 60.0
    relative_budget_seconds = max(
        cold_seconds * 1.50,
        cold_seconds + 0.10,
    )
    passed = bool(
        cold_payload["preflight_pass"] is True
        and warm_payload["preflight_pass"] is True
        and cold_seconds < absolute_budget_seconds
        and warm_seconds <= relative_budget_seconds
    )

    payload = base_payload(
        231,
        "PERFORMANCE_BUDGET_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "PERFORMANCE_BUDGET_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "cold_seconds": round(cold_seconds, 6),
            "warm_seconds": round(warm_seconds, 6),
            "absolute_budget_seconds": absolute_budget_seconds,
            "relative_budget_seconds": round(
                relative_budget_seconds,
                6,
            ),
            "warm_to_cold_ratio": round(
                warm_seconds / cold_seconds
                if cold_seconds > 0
                else 0.0,
                6,
            ),
            "passed": passed,
        }
    )
    clear_registry_caches()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_performance_budget_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 231 Performance Budget Guard",
        payload,
        [
            f"- Cold call: `{payload['cold_seconds']}` seconds",
            f"- Warm call: `{payload['warm_seconds']}` seconds",
            f"- Warm/cold ratio: `{payload['warm_to_cold_ratio']}`",
            "- Phase 174 must remain below the broad safety budget.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
