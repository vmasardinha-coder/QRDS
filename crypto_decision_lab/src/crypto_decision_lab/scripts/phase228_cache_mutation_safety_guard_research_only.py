from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase171_shadow_readiness_requirement_registry_research_only import (
    build_shadow_readiness_requirement_registry,
)
from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    clear_registry_caches,
    project_root,
    write_json,
    write_markdown,
)


def build_cache_mutation_safety_guard(
    root: Path | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    clear_registry_caches()

    first = build_shadow_readiness_requirement_registry(resolved)
    second = build_shadow_readiness_requirement_registry(resolved)
    original_status = second["operational_status"]

    first["operational_status"] = "TAMPERED_BY_CONSUMER"
    first["canonical_data_writes"] = 999

    third = build_shadow_readiness_requirement_registry(resolved)
    mutation_isolated = bool(
        third["operational_status"] == original_status
        and third["canonical_data_writes"] == 0
        and first is not second
        and second is not third
    )
    info = build_shadow_readiness_requirement_registry.cache_info()
    passed = bool(
        mutation_isolated
        and info.misses == 1
        and info.hits >= 2
    )

    payload = base_payload(
        228,
        "CACHE_MUTATION_SAFETY_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "CACHE_MUTATION_SAFETY_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "mutation_isolated": mutation_isolated,
            "cache_hits": info.hits,
            "cache_misses": info.misses,
            "same_object_returned": first is second or second is third,
            "passed": passed,
        }
    )
    clear_registry_caches()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_cache_mutation_safety_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 228 Cache Mutation Safety Guard",
        payload,
        [
            f"- Consumer mutation isolated: `{payload['mutation_isolated']}`",
            f"- Cache hits: `{payload['cache_hits']}`",
            f"- Cache misses: `{payload['cache_misses']}`",
            "- Cached objects are never returned directly to consumers.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
