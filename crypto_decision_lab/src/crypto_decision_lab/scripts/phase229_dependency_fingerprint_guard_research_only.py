from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    REGISTRY_SPECS,
    add_standard_output_arguments,
    base_payload,
    hash_paths,
    project_root,
    test_manifest,
    write_json,
    write_markdown,
)


def dependency_paths(root: Path) -> list[Path]:
    paths = [
        root
        / "src"
        / "crypto_decision_lab"
        / "scripts"
        / "phase226_235_technical_reliability_common.py",
        root / "tests" / "conftest.py",
    ]
    for module_name, _ in REGISTRY_SPECS:
        module_file = module_name.rsplit(".", 1)[-1] + ".py"
        paths.append(
            root
            / "src"
            / "crypto_decision_lab"
            / "scripts"
            / module_file
        )
    paths.extend(test_manifest(root))
    return paths


def build_dependency_fingerprint_guard(
    root: Path | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    paths = dependency_paths(resolved)
    fingerprint = hash_paths(paths, resolved)
    second = hash_paths(paths, resolved)
    passed = bool(
        len(fingerprint) == 64
        and fingerprint == second
        and len(paths) >= 10
    )

    payload = base_payload(
        229,
        "DEPENDENCY_FINGERPRINT_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "DEPENDENCY_FINGERPRINT_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "fingerprint_sha256": fingerprint,
            "repeat_fingerprint_sha256": second,
            "fingerprint_stable": fingerprint == second,
            "dependency_file_count": len(paths),
            "test_manifest_file_count": len(test_manifest(resolved)),
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_dependency_fingerprint_guard(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 229 Dependency Fingerprint Guard",
        payload,
        [
            f"- Dependency files: `{payload['dependency_file_count']}`",
            f"- Test files: `{payload['test_manifest_file_count']}`",
            f"- Fingerprint stable: `{payload['fingerprint_stable']}`",
            "- Reused evidence must match this code and test fingerprint.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
