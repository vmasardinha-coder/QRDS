from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    cache_contracts,
    project_root,
    write_json,
    write_markdown,
)


def build_cache_contract_registry(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = project_root(root)
    contracts = cache_contracts()
    passed = bool(
        len(contracts) == 7
        and all(
            item["scope"] == "PROCESS_LOCAL"
            and item["maxsize"] == 16
            and item["copy_on_read"] is True
            and item["cache_clear_available"] is True
            and item["cache_info_available"] is True
            for item in contracts
        )
    )
    payload = base_payload(
        226,
        "CACHE_CONTRACT_REGISTRY_PASS_RESEARCH_ONLY"
        if passed
        else "CACHE_CONTRACT_REGISTRY_NEEDS_REVIEW",
    )
    payload.update(
        {
            "contracts": contracts,
            "registry_count": len(contracts),
            "process_local_only": True,
            "copy_on_read_required": True,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_cache_contract_registry(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 226 Cache Contract Registry",
        payload,
        [
            f"- Registered caches: `{payload['registry_count']}`",
            "- Cache scope: process-local.",
            "- Every caller receives a defensive deep copy.",
            "- Test isolation requires cache clearing before and after tests.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
