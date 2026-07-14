from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase174_shadow_readiness_preflight_research_only import (
    build_shadow_readiness_preflight,
)
from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    clear_registry_caches,
    project_root,
    registry_builders,
    write_json,
    write_markdown,
)


def cache_snapshot() -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for builder in registry_builders():
        info = builder.cache_info()
        rows.append(
            {
                "builder": builder.__name__,
                "hits": info.hits,
                "misses": info.misses,
                "currsize": info.currsize,
            }
        )
    return rows


def build_dag_recomputation_guard(
    root: Path | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    clear_registry_caches()

    first_payload = build_shadow_readiness_preflight(resolved)
    first = cache_snapshot()
    second_payload = build_shadow_readiness_preflight(resolved)
    second = cache_snapshot()

    misses_stable = all(
        before["misses"] == after["misses"]
        for before, after in zip(first, second, strict=True)
    )
    no_registry_recomputed = all(
        int(after["misses"]) <= 1
        for after in second
    )
    hits_increased = any(
        int(after["hits"]) > int(before["hits"])
        for before, after in zip(first, second, strict=True)
    )
    passed = bool(
        first_payload["preflight_pass"] is True
        and second_payload["preflight_pass"] is True
        and misses_stable
        and no_registry_recomputed
        and hits_increased
    )

    payload = base_payload(
        230,
        "DAG_RECOMPUTATION_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "DAG_RECOMPUTATION_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "first_snapshot": first,
            "second_snapshot": second,
            "misses_stable": misses_stable,
            "no_registry_recomputed": no_registry_recomputed,
            "hits_increased": hits_increased,
            "passed": passed,
        }
    )
    clear_registry_caches()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_dag_recomputation_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 230 DAG Recomputation Guard",
        payload,
        [
            f"- Cache misses stable: `{payload['misses_stable']}`",
            f"- No registry recomputed: `{payload['no_registry_recomputed']}`",
            f"- Cache hits increased: `{payload['hits_increased']}`",
            "- A repeated Phase 174 preflight cannot rebuild the dependency DAG.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
