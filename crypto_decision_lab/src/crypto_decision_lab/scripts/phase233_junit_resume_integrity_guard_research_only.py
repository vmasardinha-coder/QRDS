from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    add_standard_output_arguments,
    base_payload,
    parse_junit,
    project_root,
    write_json,
    write_markdown,
)


def inspect_result_group(meta_path: Path) -> dict[str, Any]:
    payload = json.loads(
        meta_path.read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        return {
            "meta": meta_path.as_posix(),
            "valid": False,
            "reason": "METADATA_NOT_OBJECT",
        }
    junit_path = meta_path.with_suffix(".xml")
    log_path = meta_path.with_suffix(".log")
    junit = parse_junit(junit_path)
    valid = bool(
        payload.get("returncode") == 0
        and payload.get("timed_out") is False
        and junit["parse_ok"] is True
        and junit["tests"] > 0
        and junit["failures"] == 0
        and junit["errors"] == 0
        and log_path.is_file()
    )
    return {
        "meta": meta_path.as_posix(),
        "junit": junit,
        "log_exists": log_path.is_file(),
        "returncode": payload.get("returncode"),
        "timed_out": payload.get("timed_out"),
        "mode": payload.get("mode"),
        "valid": valid,
    }


def build_junit_resume_integrity_guard(
    root: Path | None = None,
    *,
    full_suite_dir: Path | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    suite = (
        full_suite_dir.resolve()
        if full_suite_dir is not None
        else (
            resolved
            / "artifacts"
            / "phase216_225_robustness_trust"
            / "full_suite"
        )
    )
    meta_paths = sorted(
        suite.glob("phase225_v10_file_*.json")
    )
    groups = [
        inspect_result_group(path)
        for path in meta_paths
    ]
    valid_count = sum(
        1 for item in groups if item["valid"]
    )
    invalid_count = len(groups) - valid_count

    aggregate_junits = [
        parse_junit(
            suite / f"phase225_shard_{index}.xml"
        )
        for index in (1, 2, 3)
    ]
    aggregates_valid = all(
        item["parse_ok"] is True
        and item["tests"] > 0
        and item["failures"] == 0
        and item["errors"] == 0
        for item in aggregate_junits
    )
    passed = bool(
        groups
        and valid_count == len(groups)
        and aggregates_valid
    )

    payload = base_payload(
        233,
        "JUNIT_RESUME_INTEGRITY_GUARD_PASS_RESEARCH_ONLY"
        if passed
        else "JUNIT_RESUME_INTEGRITY_GUARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "full_suite_dir": suite.as_posix(),
            "result_group_count": len(groups),
            "valid_result_group_count": valid_count,
            "invalid_result_group_count": invalid_count,
            "aggregate_junits": aggregate_junits,
            "aggregates_valid": aggregates_valid,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    parser.add_argument("--full-suite-dir")
    args = parser.parse_args()
    payload = build_junit_resume_integrity_guard(
        Path(args.project_root) if args.project_root else None,
        full_suite_dir=(
            Path(args.full_suite_dir)
            if args.full_suite_dir
            else None
        ),
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 233 JUnit and Resume Integrity Guard",
        payload,
        [
            f"- Result groups: `{payload['result_group_count']}`",
            f"- Valid groups: `{payload['valid_result_group_count']}`",
            f"- Invalid groups: `{payload['invalid_result_group_count']}`",
            f"- Aggregate JUnits valid: `{payload['aggregates_valid']}`",
            "- Incomplete XML or inconsistent metadata cannot be reused.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
