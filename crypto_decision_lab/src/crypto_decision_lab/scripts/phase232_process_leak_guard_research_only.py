from __future__ import annotations

import argparse
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
    relevant_process_snapshot,
    write_json,
    write_markdown,
)


def build_process_leak_guard(
    root: Path | None = None,
    *,
    snapshot: Callable[[], dict[int, dict[str, Any]]] = (
        relevant_process_snapshot
    ),
    workload: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    clear_registry_caches()
    before = snapshot()
    result = (
        workload()
        if workload is not None
        else build_shadow_readiness_preflight(resolved)
    )
    after = snapshot()
    introduced = sorted(set(after) - set(before))
    relevant_introduced = []
    for pid in introduced:
        process = after[pid]
        name = str(process.get("Name", "")).lower()
        command_line = str(
            process.get("CommandLine", "")
        ).lower()
        executor_process = bool(
            "python" in name
            or "bash" in name
            or name in {"cmd", "cmd.exe"}
        )
        test_or_server_process = bool(
            "pytest" in command_line
            or "http.server" in command_line
        )
        if executor_process and test_or_server_process:
            relevant_introduced.append(process)
    passed = bool(
        result["preflight_pass"] is True
        and not relevant_introduced
    )

    payload = base_payload(
        232,
        "PROCESS_LEAK_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "PROCESS_LEAK_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "before_process_count": len(before),
            "after_process_count": len(after),
            "introduced_process_ids": introduced,
            "relevant_introduced_processes": relevant_introduced,
            "passed": passed,
        }
    )
    clear_registry_caches()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_process_leak_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 232 Process Leak Guard",
        payload,
        [
            f"- Introduced process IDs: `{payload['introduced_process_ids']}`",
            "- No pytest or HTTP server process may survive the workload.",
            "- Native runtime crashes remain an accepted residual risk.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
