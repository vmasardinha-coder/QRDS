from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase191_full_suite_execution_manifest_research_only"
    / "phase191_full_suite_execution_manifest.json"
)
DOC = (
    ROOT
    / "docs"
    / "reports"
    / "journal_replay"
    / "phase191_full_suite_execution_manifest_summary.md"
)
PHASE186 = (
    ROOT
    / "artifacts"
    / "phase186_test_inventory_research_only"
    / "phase186_test_inventory.json"
)
PHASE190 = (
    ROOT
    / "artifacts"
    / "phase190_full_integration_regression_checkpoint_research_only"
    / "phase190_full_integration_regression_checkpoint.json"
)

GATE = (
    "PHASE191_FULL_SUITE_EXECUTION_MANIFEST_"
    "RESEARCH_ONLY_READY_RESEARCH_ONLY"
)

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

PHASE_PATTERN = re.compile(
    r"phase[_-]?0*(\d{1,3})(?!\d)",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing prerequisite artifact: {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"Artifact root must be object: {path}"
    return value


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def phase_from_path(path: Path) -> int | None:
    matches = PHASE_PATTERN.findall(relative(path))
    if not matches:
        return None
    return int(matches[-1])


def test_records() -> list[dict[str, Any]]:
    tests_root = ROOT / "tests"

    paths = sorted(
        (
            path
            for path in tests_root.rglob("test_*.py")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.name
            != "test_phase191_full_suite_execution_manifest_research_only.py"
        ),
        key=lambda path: relative(path).lower(),
    )

    records = []

    for path in paths:
        records.append(
            {
                "path": relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": digest_file(path),
                "phase": phase_from_path(path),
            }
        )

    return records


def build_shards(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    containers = [
        {
            "shard_id": "A",
            "execution_phase": 192,
            "records": [],
            "total_bytes": 0,
        },
        {
            "shard_id": "B",
            "execution_phase": 193,
            "records": [],
            "total_bytes": 0,
        },
        {
            "shard_id": "C",
            "execution_phase": 194,
            "records": [],
            "total_bytes": 0,
        },
    ]

    ranked = sorted(
        records,
        key=lambda record: (
            -record["size_bytes"],
            record["path"].lower(),
        ),
    )

    for record in ranked:
        target = min(
            containers,
            key=lambda shard: (
                shard["total_bytes"],
                len(shard["records"]),
                shard["shard_id"],
            ),
        )
        target["records"].append(record)
        target["total_bytes"] += record["size_bytes"]

    shards = []

    for container in containers:
        ordered_records = sorted(
            container["records"],
            key=lambda record: record["path"].lower(),
        )
        files = [record["path"] for record in ordered_records]

        shards.append(
            {
                "shard_id": container["shard_id"],
                "execution_phase": container["execution_phase"],
                "file_count": len(files),
                "total_bytes": container["total_bytes"],
                "files": files,
            }
        )

    return shards


def manifest_digest(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()

    for record in sorted(records, key=lambda item: item["path"]):
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\n")

    return digest.hexdigest()


def validate_prerequisites(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    phase186 = load_json(PHASE186)
    phase190 = load_json(PHASE190)

    assert phase186["phase"] == 186
    assert phase186["phase_status"] == "READY_RESEARCH_ONLY"
    assert phase186["pytest_collect_only"]["status"] == "PASS"

    phase186_file_count = phase186["inventory"]["test_files"]
    assert phase186_file_count == 424, (
        f"Unexpected Phase 186 baseline: {phase186_file_count}"
    )

    post_phase186_tests = [
        ROOT / "tests/unit/test_phase187_artifact_integrity_scanner_research_only.py",
        ROOT / "tests/unit/test_phase188_cross_phase_dependency_audit_research_only.py",
        ROOT / "tests/unit/test_phase189_lightweight_ci_research_only.py",
        ROOT / "tests/unit/test_phase190_full_integration_regression_checkpoint_research_only.py",
    ]

    missing_post_phase186_tests = [
        relative(path)
        for path in post_phase186_tests
        if not path.exists()
    ]
    assert not missing_post_phase186_tests, (
        "Missing Phase 187-190 tests: "
        f"{missing_post_phase186_tests}"
    )

    expected_current_count = phase186_file_count + len(post_phase186_tests)
    assert expected_current_count == 428
    assert len(records) == expected_current_count, (
        f"Test inventory drift for target 0-190: "
        f"current={len(records)}, expected={expected_current_count}"
    )

    assert phase190["phase"] == 190
    assert phase190["phase_status"] == "READY_RESEARCH_ONLY"
    assert phase190["artifact_checkpoint"] is True
    assert phase190["cross_artifact_consistency"] is True
    assert (
        phase190["batch_gate"]
        == "PHASE186_190_BATCH_READY_RESEARCH_ONLY"
    )

    return {
        "phase186_test_inventory_count": phase186_file_count,
        "post_phase186_added_test_files": len(post_phase186_tests),
        "current_frozen_test_count": expected_current_count,
        "phase186_collect_status": (
            phase186["pytest_collect_only"]["status"]
        ),
        "phase190_gate": phase190["gate"],
        "phase190_batch_gate": phase190["batch_gate"],
        "phase190_artifact_checkpoint": (
            phase190["artifact_checkpoint"]
        ),
        "phase190_cross_artifact_consistency": (
            phase190["cross_artifact_consistency"]
        ),
    }


def validate_manifest(
    records: list[dict[str, Any]],
    shards: list[dict[str, Any]],
) -> dict[str, Any]:
    source_paths = [record["path"] for record in records]
    assigned_paths = [
        path
        for shard in shards
        for path in shard["files"]
    ]

    source_set = set(source_paths)
    assigned_set = set(assigned_paths)

    duplicate_count = len(assigned_paths) - len(assigned_set)
    missing = sorted(source_set - assigned_set)
    unexpected = sorted(assigned_set - source_set)

    assert len(source_paths) == len(source_set), (
        "Duplicate test paths in source inventory."
    )
    assert duplicate_count == 0, (
        f"Duplicate shard assignments: {duplicate_count}"
    )
    assert not missing, f"Missing shard assignments: {missing}"
    assert not unexpected, f"Unexpected shard assignments: {unexpected}"
    assert len(assigned_paths) == len(source_paths)

    shard_counts = {
        shard["shard_id"]: shard["file_count"]
        for shard in shards
    }
    shard_bytes = {
        shard["shard_id"]: shard["total_bytes"]
        for shard in shards
    }

    return {
        "source_file_count": len(source_paths),
        "assigned_file_count": len(assigned_paths),
        "unique_assigned_file_count": len(assigned_set),
        "duplicate_assignment_count": duplicate_count,
        "missing_assignment_count": len(missing),
        "unexpected_assignment_count": len(unexpected),
        "missing_assignments": missing,
        "unexpected_assignments": unexpected,
        "shard_file_counts": shard_counts,
        "shard_total_bytes": shard_bytes,
        "coverage_complete": True,
    }


def write_document(payload: dict[str, Any]) -> None:
    shard_summary = [
        {
            "shard_id": shard["shard_id"],
            "execution_phase": shard["execution_phase"],
            "file_count": shard["file_count"],
            "total_bytes": shard["total_bytes"],
        }
        for shard in payload["execution_manifest"]["shards"]
    ]

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(
        f"""# Phase 191 â€” Full-Suite Execution Manifest 0â€“190

## Gate

```text
{payload["gate"]}
```

## Result

```text
Phase status: {payload["phase_status"]}
Execution status: {payload["execution_status"]}
Frozen test files: {payload["execution_manifest"]["total_test_files"]}
Manifest digest: {payload["execution_manifest"]["manifest_sha256"]}
Coverage complete: True
Duplicate assignments: 0
Missing assignments: 0
Unexpected assignments: 0
Full suite: NOT_RUN_MANIFEST_ONLY
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Shard plan

```json
{json.dumps(shard_summary, indent=2, ensure_ascii=False)}
```

## Manifest validation

```json
{json.dumps(payload["manifest_validation"], indent=2, ensure_ascii=False)}
```

## Prerequisites

```json
{json.dumps(payload["prerequisite_validation"], indent=2, ensure_ascii=False)}
```

## Execution contract

- Phase 192 executes shard A.
- Phase 193 executes shard B.
- Phase 194 executes shard C.
- Phase 195 consolidates the three immutable shard results.
- Every frozen test file must be executed exactly once.
- Any failure or error blocks progression until diagnosed.
- The full-suite checkpoint may declare PASS only when all three shards pass.

The manifest freezes the 428 test files that existed at the Phase 190
checkpoint. The Phase 191 test itself and later sprint tests are not part of
the 0â€“190 regression target.

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
""",
        encoding="utf-8",
    )


def main() -> int:
    records = test_records()
    prerequisites = validate_prerequisites(records)
    shards = build_shards(records)
    validation = validate_manifest(records, shards)

    payload = {
        "schema_version": "1.0.0",
        "phase": 191,
        "phase_name": (
            "FULL_SUITE_EXECUTION_MANIFEST_RESEARCH_ONLY"
        ),
        "gate": GATE,
        "phase_status": "READY_RESEARCH_ONLY",
        "execution_status": "MANIFEST_READY_NOT_EXECUTED",
        "full_suite_status": "NOT_RUN_MANIFEST_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "scope": {
            "regression_target_start": 0,
            "regression_target_end": 190,
            "frozen_at_phase190_checkpoint": True,
            "test_execution_performed": False,
            "sharded_execution_required": True,
            "shard_count": 3,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "prerequisite_validation": prerequisites,
        "execution_manifest": {
            "total_test_files": len(records),
            "total_test_bytes": sum(
                record["size_bytes"] for record in records
            ),
            "manifest_sha256": manifest_digest(records),
            "inventory_records": records,
            "shards": shards,
        },
        "manifest_validation": validation,
        "next_phase_candidate": (
            "PHASE192_FULL_SUITE_SHARD_A_EXECUTION"
        ),
        "next_phase_blocked_by_needs_review": False,
    }

    assert payload["locks"]["promotion_allowed"] is False
    assert payload["locks"]["decision_layer_allowed"] is False
    assert payload["locks"]["shadow_decision_allowed"] is False
    assert payload["locks"]["canonical_data_writes"] == 0

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_document(payload)

    print(GATE)
    print("Phase status: READY_RESEARCH_ONLY")
    print("Execution status: MANIFEST_READY_NOT_EXECUTED")
    print("Full suite status: NOT_RUN_MANIFEST_ONLY")
    print("Frozen test files:", len(records))
    print("Manifest SHA256:", payload["execution_manifest"]["manifest_sha256"])

    for shard in shards:
        print(
            f'Shard {shard["shard_id"]}: '
            f'{shard["file_count"]} files | '
            f'{shard["total_bytes"]} bytes | '
            f'Phase {shard["execution_phase"]}'
        )

    print("Coverage complete: True")
    print("Duplicate assignments: 0")
    print("Missing assignments: 0")
    print("Unexpected assignments: 0")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Promotion allowed: False")
    print("Decision layer allowed: False")
    print("Shadow decision allowed: False")
    print("canonical_data_writes: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
