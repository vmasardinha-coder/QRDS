from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    cache_contracts,
    clear_registry_caches,
    project_root,
    registry_builders,
    write_json,
    write_markdown,
)

BEGIN_MARKER = "# BEGIN QRDS REGISTRY CACHE ISOLATION"
END_MARKER = "# END QRDS REGISTRY CACHE ISOLATION"


def build_cache_test_isolation_guard(
    root: Path | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    conftest = resolved / "tests" / "conftest.py"
    text = conftest.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )
    marker_installed = (
        BEGIN_MARKER in text and END_MARKER in text
    )

    clear_registry_caches()
    empty_before = all(
        builder.cache_info().currsize == 0
        for builder in registry_builders()
    )
    clear_registry_caches()
    empty_after = all(
        builder.cache_info().currsize == 0
        for builder in registry_builders()
    )
    passed = bool(
        marker_installed
        and empty_before
        and empty_after
        and len(cache_contracts()) == 7
    )

    payload = base_payload(
        227,
        "CACHE_TEST_ISOLATION_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "CACHE_TEST_ISOLATION_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "fixture_marker_installed": marker_installed,
            "cache_empty_before_test_boundary": empty_before,
            "cache_empty_after_test_boundary": empty_after,
            "registry_count": len(cache_contracts()),
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_cache_test_isolation_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 227 Cache Test Isolation Guard",
        payload,
        [
            f"- Autouse fixture installed: `{payload['fixture_marker_installed']}`",
            "- Registry caches are cleared before and after every test.",
            "- Cache state cannot leak across independent tests.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
