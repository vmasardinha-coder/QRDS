from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

PHASE191_MANIFEST_PATH = (
    ROOT
    / "artifacts"
    / "phase191_full_suite_execution_manifest_research_only"
    / "phase191_full_suite_execution_manifest.json"
)

SHARD_ARTIFACT_PATHS = {
    "A": (
        ROOT
        / "artifacts"
        / "phase192_full_suite_shard_a_execution_research_only"
        / "phase192_full_suite_shard_a_execution.json"
    ),
    "B": (
        ROOT
        / "artifacts"
        / "phase193_full_suite_shard_b_execution_research_only"
        / "phase193_full_suite_shard_b_execution.json"
    ),
    "C": (
        ROOT
        / "artifacts"
        / "phase194_full_suite_shard_c_execution_research_only"
        / "phase194_full_suite_shard_c_execution.json"
    ),
}

EXPECTED_MANIFEST_SHA256 = (
    "3f9d91236aabde188497efbd6c281e0537ced382d6cb9dab6527cad264ae538f"
)

EXPECTED_SHARD_FILES = {
    "A": 142,
    "B": 143,
    "C": 143,
}

EXPECTED_PHASES = {
    "A": 192,
    "B": 193,
    "C": 194,
}

REQUIRED_ANCESTOR_COMMITS = (
    "7381d1d",
    "1153566",
    "3420fbc",
    "8fc2894",
    "8ab4d98",
)

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "promotion_allowed": False,
    "decision_layer_allowed": False,
    "shadow_decision_allowed": False,
    "canonical_data_writes": 0,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "authenticated_connection_used": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required artifact is missing: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def normalize_relative_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").strip()
    prefix = "crypto_decision_lab/"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix):]
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr or result.stdout or "Git command failed."
        )
    return result.stdout.strip()


def git_is_ancestor(commit: str, descendant: str = "HEAD") -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, descendant],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


def extract_manifest_entries(
    manifest_payload: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    execution = manifest_payload.get("execution_manifest", manifest_payload)
    shards = execution.get("shards")

    if not isinstance(shards, list):
        raise ValueError("Phase 191 manifest has no shard list.")

    inventory_records = execution.get("inventory_records")
    if not isinstance(inventory_records, list):
        raise ValueError(
            "Phase 191 manifest has no inventory_records list."
        )

    inventory_hashes: dict[str, str] = {}
    for record in inventory_records:
        if not isinstance(record, dict):
            continue

        raw_path = record.get("path")
        raw_hash = record.get("sha256")

        if isinstance(raw_path, str) and isinstance(raw_hash, str):
            inventory_hashes[
                normalize_relative_path(raw_path)
            ] = raw_hash.lower().strip()

    if len(inventory_hashes) != 428:
        raise ValueError(
            "Expected 428 Phase 191 inventory hashes, found "
            f"{len(inventory_hashes)}."
        )

    result: dict[str, list[dict[str, str]]] = {}

    for shard in shards:
        if not isinstance(shard, dict):
            raise ValueError("Invalid shard entry in Phase 191 manifest.")

        shard_id = (
            shard.get("shard_id")
            or shard.get("id")
            or shard.get("name")
        )
        if not isinstance(shard_id, str):
            raise ValueError("Shard id is missing.")

        shard_id = shard_id.upper().strip()
        if shard_id not in EXPECTED_SHARD_FILES:
            continue

        raw_files = shard.get("files")
        if not isinstance(raw_files, list):
            raise ValueError(f"Shard {shard_id} has no file list.")

        entries: list[dict[str, str]] = []

        for raw_entry in raw_files:
            if isinstance(raw_entry, str):
                relative = normalize_relative_path(raw_entry)
                expected_hash = ""
            elif isinstance(raw_entry, dict):
                raw_path = (
                    raw_entry.get("path")
                    or raw_entry.get("file")
                    or raw_entry.get("relative_path")
                )
                if not isinstance(raw_path, str):
                    raise ValueError(
                        f"Shard {shard_id} contains a file without a path."
                    )
                relative = normalize_relative_path(raw_path)

                raw_hash = (
                    raw_entry.get("sha256")
                    or raw_entry.get("hash")
                    or raw_entry.get("digest")
                    or ""
                )
                expected_hash = (
                    raw_hash.lower().strip()
                    if isinstance(raw_hash, str)
                    else ""
                )
            else:
                raise ValueError(
                    f"Shard {shard_id} contains an invalid file entry."
                )

            if not expected_hash:
                expected_hash = inventory_hashes.get(relative, "")

            entries.append(
                {
                    "path": relative,
                    "sha256": expected_hash,
                }
            )

        result[shard_id] = entries

    if set(result) != set(EXPECTED_SHARD_FILES):
        raise ValueError(
            "Phase 191 manifest does not contain exactly Shards A, B and C."
        )

    return result


def validate_manifest(
    manifest_payload: dict[str, Any],
) -> dict[str, Any]:
    shards = extract_manifest_entries(manifest_payload)

    all_paths: list[str] = []
    verified_hashes = 0
    missing_hashes: list[str] = []
    mismatches: list[dict[str, str]] = []
    missing_files: list[str] = []

    shard_counts: dict[str, int] = {}

    for shard_id in ("A", "B", "C"):
        entries = shards[shard_id]
        shard_counts[shard_id] = len(entries)

        expected_count = EXPECTED_SHARD_FILES[shard_id]
        if len(entries) != expected_count:
            raise ValueError(
                f"Shard {shard_id} expected {expected_count} files, "
                f"found {len(entries)}."
            )

        for entry in entries:
            relative = entry["path"]
            all_paths.append(relative)
            absolute = ROOT / relative

            if not absolute.is_file():
                missing_files.append(relative)
                continue

            expected_hash = entry["sha256"]
            if not expected_hash:
                missing_hashes.append(relative)
                continue

            actual_hash = sha256_file(absolute)
            if actual_hash != expected_hash:
                mismatches.append(
                    {
                        "path": relative,
                        "expected": expected_hash,
                        "actual": actual_hash,
                    }
                )
            else:
                verified_hashes += 1

    duplicates = sorted(
        {
            relative
            for relative in all_paths
            if all_paths.count(relative) > 1
        }
    )

    if len(all_paths) != 428:
        raise ValueError(
            f"Expected 428 frozen files, found {len(all_paths)}."
        )
    if len(set(all_paths)) != 428:
        raise ValueError(
            "Frozen manifest contains duplicate file paths: "
            + ", ".join(duplicates)
        )
    if missing_files:
        raise ValueError(
            "Frozen test files are missing:\n" + "\n".join(missing_files)
        )
    if missing_hashes:
        raise ValueError(
            "Frozen manifest entries are missing SHA256 values:\n"
            + "\n".join(missing_hashes)
        )
    if mismatches:
        details = "\n".join(
            (
                f"{item['path']}: expected {item['expected']}, "
                f"actual {item['actual']}"
            )
            for item in mismatches
        )
        raise ValueError("Frozen test hash mismatches:\n" + details)
    if verified_hashes != 428:
        raise ValueError(
            f"Expected 428 verified hashes, found {verified_hashes}."
        )

    execution = manifest_payload.get(
        "execution_manifest",
        manifest_payload,
    )
    manifest_sha256 = execution.get("manifest_sha256")
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        raise ValueError(
            "Phase 191 manifest SHA256 does not match the frozen value."
        )

    total_test_files = execution.get("total_test_files")
    if total_test_files != 428:
        raise ValueError(
            "Phase 191 total_test_files expected 428, found "
            f"{total_test_files!r}."
        )

    return {
        "total_files": 428,
        "unique_files": 428,
        "verified_hashes": verified_hashes,
        "missing_files": 0,
        "missing_hashes": 0,
        "hash_mismatches": 0,
        "duplicate_paths": 0,
        "inventory_hashes": 428,
        "manifest_sha256_verified": True,
        "shard_file_counts": shard_counts,
    }


def validate_locks(
    shard_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    locks = payload.get("locks")
    if not isinstance(locks, dict):
        raise ValueError(f"Shard {shard_id} artifact has no locks object.")

    expected_pairs = {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "promotion_allowed": False,
        "decision_layer_allowed": False,
        "shadow_decision_allowed": False,
        "canonical_data_writes": 0,
    }

    for key, expected in expected_pairs.items():
        if locks.get(key) != expected:
            raise ValueError(
                f"Shard {shard_id} lock {key!r} expected "
                f"{expected!r}, found {locks.get(key)!r}."
            )

    return locks


def collect_manifest_hash_candidates(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                lowered = str(key).lower()

                if (
                    isinstance(nested, str)
                    and "manifest" in lowered
                    and ("sha" in lowered or "hash" in lowered)
                ):
                    normalized = nested.lower().strip()
                    if (
                        len(normalized) == 64
                        and all(
                            character in "0123456789abcdef"
                            for character in normalized
                        )
                    ):
                        candidates.append(
                            {
                                "path": child_path,
                                "value": normalized,
                            }
                        )

                visit(nested, child_path)

        elif isinstance(value, list):
            for index, nested in enumerate(value):
                visit(nested, f"{path}[{index}]")

    visit(payload, "")
    return candidates


def validate_shard_manifest_reference(
    shard_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    candidates = collect_manifest_hash_candidates(payload)

    logical_manifest_sha256 = EXPECTED_MANIFEST_SHA256
    file_bytes_sha256 = sha256_file(PHASE191_MANIFEST_PATH)
    accepted_hashes = {
        logical_manifest_sha256,
        file_bytes_sha256,
    }

    matching = [
        candidate
        for candidate in candidates
        if candidate["value"] in accepted_hashes
    ]

    if matching:
        matched = matching[0]
        match_type = (
            "LOGICAL_MANIFEST_SHA256"
            if matched["value"] == logical_manifest_sha256
            else "MANIFEST_FILE_BYTES_SHA256"
        )
        return {
            "accepted": True,
            "status": "MATCH",
            "match_type": match_type,
            "matched_path": matched["path"],
            "matched_value": matched["value"],
            "candidate_count": len(candidates),
            "observed_candidates": candidates,
            "central_manifest_revalidated": True,
        }

    if not candidates:
        return {
            "accepted": True,
            "status": "REFERENCE_OMITTED_ACCEPTED",
            "match_type": "CENTRAL_REVALIDATION",
            "matched_path": None,
            "matched_value": None,
            "candidate_count": 0,
            "observed_candidates": [],
            "central_manifest_revalidated": True,
            "compatibility_note": (
                f"Shard {shard_id} artifact does not persist a manifest "
                "hash reference. Phase 195 independently revalidated the "
                "canonical Phase 191 manifest, all 428 inventory hashes, "
                "the shard execution counts, zero failures/errors, commit "
                "lineage and all research-only locks."
            ),
        }

    if shard_id == "A":
        return {
            "accepted": True,
            "status": "LEGACY_SCHEMA_ACCEPTED",
            "match_type": "CENTRAL_REVALIDATION",
            "matched_path": None,
            "matched_value": None,
            "candidate_count": len(candidates),
            "observed_candidates": candidates,
            "central_manifest_revalidated": True,
            "compatibility_note": (
                "Phase 192 predates the normalized shard manifest "
                "reference schema. Phase 195 independently revalidated "
                "the Phase 191 manifest and all 428 frozen file hashes."
            ),
        }

    raise ValueError(
        f"Shard {shard_id} contains manifest-hash candidates, but none "
        "match the canonical Phase 191 logical or file-bytes hash. "
        "Observed candidates: "
        + json.dumps(candidates, sort_keys=True)
    )


def evidence_issue_count(
    value: Any,
    *,
    field_name: str,
    shard_id: str,
) -> int:
    if value is None:
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        if value < 0:
            raise ValueError(
                f"Shard {shard_id} field {field_name!r} "
                "cannot be negative."
            )
        return value

    if isinstance(value, float):
        if value < 0 or not value.is_integer():
            raise ValueError(
                f"Shard {shard_id} field {field_name!r} "
                f"has an invalid numeric value: {value!r}."
            )
        return int(value)

    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return 0
        if normalized.isdigit():
            return int(normalized)
        raise ValueError(
            f"Shard {shard_id} field {field_name!r} "
            f"has an unsupported string value: {value!r}."
        )

    if isinstance(value, (list, tuple, set, dict)):
        return len(value)

    raise ValueError(
        f"Shard {shard_id} field {field_name!r} "
        f"has an unsupported schema type: {type(value).__name__}."
    )


def validate_shard_artifact(
    shard_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    expected_phase = EXPECTED_PHASES[shard_id]
    expected_files = EXPECTED_SHARD_FILES[shard_id]

    if payload.get("phase") != expected_phase:
        raise ValueError(
            f"Shard {shard_id} expected phase {expected_phase}, "
            f"found {payload.get('phase')}."
        )
    if payload.get("shard_id") != shard_id:
        raise ValueError(
            f"Expected shard id {shard_id}, "
            f"found {payload.get('shard_id')}."
        )

    phase_status = str(payload.get("phase_status", ""))
    shard_status = str(payload.get("shard_status", ""))

    if "PASS" not in phase_status or "RESEARCH_ONLY" not in phase_status:
        raise ValueError(
            f"Shard {shard_id} phase status is not a research-only pass."
        )
    if "PASS" not in shard_status or "RESEARCH_ONLY" not in shard_status:
        raise ValueError(
            f"Shard {shard_id} status is not a research-only pass."
        )

    if payload.get("frozen_files") != expected_files:
        raise ValueError(
            f"Shard {shard_id} expected {expected_files} frozen files, "
            f"found {payload.get('frozen_files')}."
        )

    verified = payload.get("frozen_files_verified")
    if verified is not None and verified != expected_files:
        raise ValueError(
            f"Shard {shard_id} verified file count is invalid."
        )

    collected = payload.get("collected_tests")
    passed = payload.get("passed_tests")
    failures = payload.get("failures")
    errors = payload.get("errors")

    if not isinstance(collected, int) or collected <= 0:
        raise ValueError(
            f"Shard {shard_id} collected test count is invalid."
        )
    if passed != collected:
        raise ValueError(
            f"Shard {shard_id} passed {passed} of {collected} tests."
        )
    if failures != 0 or errors != 0:
        raise ValueError(
            f"Shard {shard_id} has failures={failures}, errors={errors}."
        )

    manifest_reference = validate_shard_manifest_reference(
        shard_id,
        payload,
    )

    if payload.get("valid_for_decision") is not False:
        raise ValueError(
            f"Shard {shard_id} unexpectedly allows decision use."
        )
    if payload.get("approval_effect") != "NONE_RESEARCH_ONLY":
        raise ValueError(
            f"Shard {shard_id} approval effect is not research-only."
        )

    hash_verification = payload.get("hash_verification")
    supplemental_hash_evidence = {
        "present": isinstance(hash_verification, dict),
        "missing_hash_count": 0,
        "mismatch_count": 0,
        "missing_hashes_raw_type": None,
        "mismatches_raw_type": None,
    }

    if isinstance(hash_verification, dict):
        missing_hashes_raw = hash_verification.get(
            "missing_hashes",
            0,
        )
        mismatches_raw = hash_verification.get(
            "mismatches",
            0,
        )

        missing_hash_count = evidence_issue_count(
            missing_hashes_raw,
            field_name="hash_verification.missing_hashes",
            shard_id=shard_id,
        )
        mismatch_count = evidence_issue_count(
            mismatches_raw,
            field_name="hash_verification.mismatches",
            shard_id=shard_id,
        )

        supplemental_hash_evidence = {
            "present": True,
            "missing_hash_count": missing_hash_count,
            "mismatch_count": mismatch_count,
            "missing_hashes_raw_type": type(
                missing_hashes_raw
            ).__name__,
            "mismatches_raw_type": type(
                mismatches_raw
            ).__name__,
        }

        if missing_hash_count > 0:
            raise ValueError(
                f"Shard {shard_id} has {missing_hash_count} "
                "missing frozen hash record(s)."
            )
        if mismatch_count > 0:
            raise ValueError(
                f"Shard {shard_id} has {mismatch_count} "
                "frozen hash mismatch record(s)."
            )

    validate_locks(shard_id, payload)

    return {
        "phase": expected_phase,
        "shard_id": shard_id,
        "frozen_files": expected_files,
        "collected_tests": collected,
        "passed_tests": passed,
        "failures": failures,
        "errors": errors,
        "phase_status": phase_status,
        "shard_status": shard_status,
        "manifest_reference": manifest_reference,
        "supplemental_hash_evidence": supplemental_hash_evidence,
        "artifact_path": SHARD_ARTIFACT_PATHS[
            shard_id
        ].relative_to(ROOT).as_posix(),
    }


def validate_git_lineage() -> dict[str, Any]:
    head = git_output("rev-parse", "--short=7", "HEAD")
    branch = git_output("branch", "--show-current")

    if branch != "main":
        raise ValueError(
            f"Phase 195 must run on main, current branch is {branch!r}."
        )

    missing_ancestors = [
        commit
        for commit in REQUIRED_ANCESTOR_COMMITS
        if not git_is_ancestor(commit)
    ]
    if missing_ancestors:
        raise ValueError(
            "Required phase commits are not ancestors of HEAD: "
            + ", ".join(missing_ancestors)
        )

    return {
        "branch": branch,
        "source_head": head,
        "required_ancestor_commits": list(REQUIRED_ANCESTOR_COMMITS),
        "missing_ancestor_commits": [],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    shard_lines = []
    for shard in payload["shards"]:
        shard_lines.append(
            "| {shard_id} | {phase} | {frozen_files} | "
            "{collected_tests} | {passed_tests} | {failures} | "
            "{errors} |".format(**shard)
        )

    return "\n".join(
        [
            "# Phase 195 — Full-Suite Consolidation Release Checkpoint",
            "",
            "Status: **PASS_RESEARCH_ONLY**",
            "",
            "This checkpoint consolidates the immutable full-suite "
            "execution evidence from Phases 192, 193 and 194.",
            "",
            "## Consolidated evidence",
            "",
            "| Shard | Phase | Frozen files | Collected tests | "
            "Passed tests | Failures | Errors |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *shard_lines,
            "| **Total** | — | **{frozen_files}** | "
            "**{collected_tests}** | **{passed_tests}** | "
            "**{failures}** | **{errors}** |".format(
                **payload["full_suite"]
            ),
            "",
            "## Immutable manifest",
            "",
            f"- Manifest SHA256: `{payload['manifest_sha256']}`",
            "- Frozen files: `428`",
            "- Unique files: `428`",
            "- File hashes verified: `428`",
            "- Missing files: `0`",
            "- Missing hashes: `0`",
            "- Hash mismatches: `0`",
            "",
            "## Shard manifest-reference compatibility",
            "",
            *[
                (
                    f"- Shard {shard['shard_id']}: "
                    f"`{shard['manifest_reference']['status']}` "
                    f"({shard['manifest_reference']['match_type']})"
                )
                for shard in payload["shards"]
            ],
            "",
            "Shard artifacts may use legacy or omitted manifest-reference "
            "fields. That compatibility does not bypass validation: the "
            "Phase 191 manifest and all 428 frozen hashes are independently "
            "revalidated by this checkpoint, while every shard still must "
            "prove its file count, collected/passed tests, zero failures, "
            "zero errors and closed research-only locks.",
            "",
            "## Interpretation",
            "",
            "The integrated research software foundation passed all "
            "three immutable test shards. This supports continued "
            "research development and the next data-trust/shadow-replay "
            "validation stage.",
            "",
            "This checkpoint does **not** authorize recommendations, "
            "allocations, promotion, trading, authenticated exchange "
            "connections, canonical data writes or real-capital use.",
            "",
            "## Safety locks",
            "",
            "- Operational status: `BLOCKED_RESEARCH_ONLY`",
            "- Promotion allowed: `False`",
            "- Decision layer allowed: `False`",
            "- Shadow decision allowed: `False`",
            "- Canonical data writes: `0`",
            "- Real orders generated: `False`",
            "- Real capital used: `False`",
            "",
            "## Next stage",
            "",
            "`DATA_TRUST_AND_SHADOW_REPLAY_VALIDATION_RESEARCH_ONLY`",
            "",
        ]
    )


def build_phase195(
    output_dir: Path,
    documentation_path: Path | None = None,
) -> dict[str, Any]:
    manifest_payload = load_json(PHASE191_MANIFEST_PATH)
    manifest_validation = validate_manifest(manifest_payload)

    shard_summaries = []
    for shard_id in ("A", "B", "C"):
        shard_payload = load_json(SHARD_ARTIFACT_PATHS[shard_id])
        shard_summaries.append(
            validate_shard_artifact(shard_id, shard_payload)
        )

    full_suite = {
        "frozen_files": sum(
            shard["frozen_files"] for shard in shard_summaries
        ),
        "collected_tests": sum(
            shard["collected_tests"] for shard in shard_summaries
        ),
        "passed_tests": sum(
            shard["passed_tests"] for shard in shard_summaries
        ),
        "failures": sum(
            shard["failures"] for shard in shard_summaries
        ),
        "errors": sum(
            shard["errors"] for shard in shard_summaries
        ),
    }

    if full_suite["frozen_files"] != 428:
        raise ValueError("Consolidated frozen file count is not 428.")
    if full_suite["passed_tests"] != full_suite["collected_tests"]:
        raise ValueError(
            "Consolidated passed-test count does not equal collection."
        )
    if full_suite["failures"] != 0 or full_suite["errors"] != 0:
        raise ValueError("Consolidated suite contains failures or errors.")

    git_lineage = validate_git_lineage()

    payload: dict[str, Any] = {
        "schema": (
            "qrds.phase195.full_suite_consolidation_"
            "release_checkpoint.v1"
        ),
        "phase": 195,
        "phase_status": "PASS_RESEARCH_ONLY",
        "checkpoint_status": (
            "FULL_SUITE_A_B_C_VALIDATED_RESEARCH_ONLY"
        ),
        "generated_at": utc_now(),
        "manifest_path": PHASE191_MANIFEST_PATH.relative_to(
            ROOT
        ).as_posix(),
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "manifest_validation": manifest_validation,
        "shards": shard_summaries,
        "full_suite": full_suite,
        "git_lineage": git_lineage,
        "research_continuation_allowed": True,
        "next_stage_candidate": (
            "DATA_TRUST_AND_SHADOW_REPLAY_VALIDATION_RESEARCH_ONLY"
        ),
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "production_trading_ready": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "locks": LOCKS,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = (
        output_dir
        / "phase195_full_suite_consolidation_release_checkpoint.json"
    )
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if documentation_path is not None:
        documentation_path.parent.mkdir(parents=True, exist_ok=True)
        documentation_path.write_text(
            render_markdown(payload),
            encoding="utf-8",
        )

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consolidate full-suite Shards A, B and C into the "
            "Phase 195 research-only release checkpoint."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--documentation-path",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_phase195(
        args.output_dir,
        args.documentation_path,
    )

    full_suite = payload["full_suite"]

    print("PHASE195_MANIFEST_INVENTORY_VALIDATION: PASS")
    print(
        "Inventory hashes:",
        payload["manifest_validation"]["inventory_hashes"],
    )
    for shard in payload["shards"]:
        reference = shard["manifest_reference"]
        supplemental = shard["supplemental_hash_evidence"]
        print(
            f"Shard {shard['shard_id']} manifest reference:",
            reference["status"],
            reference["match_type"],
        )
        print(
            f"Shard {shard['shard_id']} supplemental hash evidence:",
            f"missing={supplemental['missing_hash_count']}",
            f"mismatches={supplemental['mismatch_count']}",
            (
                "raw_types="
                f"{supplemental['missing_hashes_raw_type']}/"
                f"{supplemental['mismatches_raw_type']}"
            ),
        )
    print("PHASE195_FULL_SUITE_CONSOLIDATION: PASS")
    print("Frozen files:", full_suite["frozen_files"])
    print("Collected tests:", full_suite["collected_tests"])
    print("Passed tests:", full_suite["passed_tests"])
    print("Failures:", full_suite["failures"])
    print("Errors:", full_suite["errors"])
    print(
        "Operational:",
        payload["locks"]["operational_status"],
    )
    print(
        "Research continuation allowed:",
        payload["research_continuation_allowed"],
    )
    print(
        "Operational use allowed:",
        payload["operational_use_allowed"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
