from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import (
    BASELINE_PHASE375_HEAD,
    LOCKS,
    ROOT,
    base_payload,
    fingerprint,
    parse_junit,
    read_json,
    sha256_file,
    utc_now_iso,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)

MIN_TEST_FILES = 614
MIN_TESTS = 1521


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _test_manifest() -> list[dict[str, Any]]:
    return [
        {"path": _relative(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted((ROOT / "tests").rglob("test_*.py"))
        if path.is_file()
    ]


def _assign_shards(records: list[dict[str, Any]], count: int = 3) -> list[list[dict[str, Any]]]:
    shards: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    totals = [0] * count
    for record in sorted(records, key=lambda item: (-int(item["size_bytes"]), item["path"])):
        index = min(range(count), key=lambda candidate: (totals[candidate], candidate))
        shards[index].append(record)
        totals[index] += int(record["size_bytes"])
    for shard in shards:
        shard.sort(key=lambda item: item["path"])
    return shards


def _parse_junit(path: Path) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0") or "0"))
    return totals


def _git_status_paths() -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    parts = [part for part in result.stdout.split(b"\0") if part]
    output: dict[str, str] = {}
    index = 0
    while index < len(parts):
        raw = parts[index].decode("utf-8", errors="surrogateescape")
        status = raw[:2]
        path = raw[3:].replace("\\", "/")
        if path.startswith("crypto_decision_lab/"):
            path = path[len("crypto_decision_lab/"):]
        if status and status[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            path = parts[index].decode("utf-8", errors="surrogateescape").replace("\\", "/")
            if path.startswith("crypto_decision_lab/"):
                path = path[len("crypto_decision_lab/"):]
        output[path] = status
        index += 1
    return output


def _cleanup_test_side_effects(before: dict[str, str], protected_roots: tuple[str, ...] = ()) -> dict[str, Any]:
    after = _git_status_paths()
    new_paths = sorted(set(after) - set(before))
    restored: list[str] = []
    removed: list[str] = []
    refused: list[str] = []
    known_prefixes = ("artifacts/", "docs/reports/")
    for relative in new_paths:
        if any(relative == root.rstrip("/") or relative.startswith(root.rstrip("/") + "/") for root in protected_roots):
            continue
        status = after[relative]
        candidate = (ROOT / relative).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            refused.append(relative)
            continue
        if status == "??":
            if not relative.startswith(known_prefixes):
                refused.append(relative)
                continue
            if candidate.is_file() or candidate.is_symlink():
                candidate.unlink()
                removed.append(relative)
            elif candidate.is_dir():
                shutil.rmtree(candidate)
                removed.append(relative)
            continue
        result = subprocess.run(["git", "checkout", "--", relative], cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            restored.append(relative)
        else:
            refused.append(relative)
    if refused:
        raise RuntimeError("Global-suite generated unexpected paths: " + ", ".join(refused))
    return {"restored_tracked_paths": restored, "removed_generated_untracked_paths": removed, "refused_paths": refused}


def _safe_name(relative: str) -> str:
    return f"{Path(relative).stem[:80]}_{hashlib.sha256(relative.encode()).hexdigest()[:12]}"


def run_resumable_full_suite(output_dir: Path, *, per_file_timeout_seconds: int = 1800) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    junit_dir = output_dir / "junit"
    log_dir = output_dir / "logs"
    junit_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    progress_path = output_dir / "phase385_full_suite_progress.json"
    manifest_before = _test_manifest()
    if len(manifest_before) < MIN_TEST_FILES:
        raise RuntimeError(f"Test inventory regression: expected at least {MIN_TEST_FILES}, found {len(manifest_before)}.")
    manifest_fingerprint = hashlib.sha256(
        json.dumps(manifest_before, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    baseline_status = _git_status_paths()
    protected = _relative(output_dir)
    existing: dict[str, Any] = {}
    if progress_path.is_file():
        try:
            loaded = read_json(progress_path)
            if loaded.get("manifest_fingerprint") == manifest_fingerprint:
                existing = dict(loaded.get("results", {}))
        except Exception:
            existing = {}
    results: dict[str, Any] = {}
    reused = 0
    executed = 0
    started = time.monotonic()
    shards = _assign_shards(manifest_before)
    ordered = [record for shard in shards for record in shard]
    for index, record in enumerate(ordered, 1):
        relative = str(record["path"])
        prior = existing.get(relative)
        if isinstance(prior, dict) and prior.get("status") == "PASS" and prior.get("sha256") == record["sha256"]:
            results[relative] = prior
            reused += 1
            continue
        name = _safe_name(relative)
        junit = junit_dir / f"{name}.xml"
        log = log_dir / f"{name}.log"
        command = [sys.executable, "-m", "pytest", "-q", "--tb=long", f"--junitxml={junit}", str(ROOT / relative)]
        environment = os.environ.copy()
        git_bash = Path(r"C:\Program Files\Git\bin")
        if git_bash.exists():
            environment["PATH"] = str(git_bash) + os.pathsep + environment.get("PATH", "")
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=per_file_timeout_seconds, check=False)
            log.write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8", errors="replace")
            totals = _parse_junit(junit) if junit.is_file() else {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
            status = "PASS" if result.returncode == 0 and totals["failures"] == 0 and totals["errors"] == 0 else "FAIL"
            item = {"status": status, "sha256": record["sha256"], "returncode": result.returncode, "junit": _relative(junit), "log": _relative(log), "totals": totals}
        except subprocess.TimeoutExpired as exc:
            log.write_text(f"TIMEOUT after {per_file_timeout_seconds}s\n{exc}", encoding="utf-8")
            item = {"status": "TIMEOUT", "sha256": record["sha256"], "returncode": None, "junit": _relative(junit), "log": _relative(log), "totals": {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}}
        results[relative] = item
        executed += 1
        write_json(progress_path, {"phase": 385, "manifest_fingerprint": manifest_fingerprint, "updated_at_utc": utc_now_iso(), "test_file_count": len(manifest_before), "current_index": index, "results": results})
        if item["status"] != "PASS":
            raise RuntimeError(f"Global-suite file failed: {relative}; status={item['status']}; log={item['log']}.")
    cleanup = _cleanup_test_side_effects(baseline_status, (protected,))
    manifest_after = _test_manifest()
    stable = manifest_before == manifest_after
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for item in results.values():
        for key in totals:
            totals[key] += int(item.get("totals", {}).get(key, 0))
    passed = (
        len(results) == len(manifest_before)
        and all(item.get("status") == "PASS" for item in results.values())
        and totals["tests"] >= MIN_TESTS
        and totals["failures"] == 0
        and totals["errors"] == 0
        and stable
    )
    return {
        "mode": "RESUMABLE_FILEWISE_THREE_SHARD_MANIFEST",
        "duration_seconds": time.monotonic() - started,
        "per_file_timeout_seconds": per_file_timeout_seconds,
        "test_file_count": len(manifest_before),
        "minimum_test_file_count": MIN_TEST_FILES,
        "minimum_tests": MIN_TESTS,
        "manifest_fingerprint": manifest_fingerprint,
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": stable,
        "shard_count": 3,
        "shards": [
            {"shard": index, "file_count": len(shard), "total_bytes": sum(int(record["size_bytes"]) for record in shard), "files": [record["path"] for record in shard]}
            for index, shard in enumerate(shards, 1)
        ],
        "reused_file_count": reused,
        "executed_file_count": executed,
        "all_files_completed": len(results) == len(manifest_before),
        "totals": totals,
        "cleanup": cleanup,
        "passed": passed,
    }


def _write_tracking(payload: dict[str, Any], tracking_dir: Path) -> None:
    full = payload["global_full_suite"]
    decision = payload["next_window_decision"]
    master = f"""# QRDS Master Progress by Tens — Phase 385

## Current decision

`{decision}`

## Window 376–385

- Noncanonical research-input adoption: `{payload['candidate_dataset_adopted_noncanonical']}`
- Canonical adoption: `{payload['candidate_dataset_adopted_canonical']}`
- Candidate rows verified: `{payload['candidate_row_count']}`
- Raw inputs preserved: `{payload['raw_input_count']}`
- Release harness pass: `{payload['release_harness_pass']}`
- Global test files: `{full['test_file_count']}`
- Global tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 385

```mermaid
flowchart TD
 A[Phase 375 quality remediation PASS] --> B[Success registered]
 B --> C[Manual noncanonical adoption review]
 C --> D[Closed-family isolation]
 D --> E[Schema and lineage contract frozen]
 E --> F[Synthetic adoption dry-run]
 F --> G[Real integrity audit]
 G --> H[Rollback and raw coexistence]
 H --> I[Release harness and failure scanner]
 I --> J[Unified portal]
 J --> K[Mandatory global suite]
 K --> L[NO_ACTION_RESEARCH_ONLY]
```

**VOCE ESTA AQUI:** `{decision}`. Capital authorized: `R$ 0`.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 385

| Range | Dominant delivery | State |
|---|---|---|
| 0–365 | Foundation, closed scientific families and data-remediation governance | Complete |
| 366–375 | One frozen real-data quality evaluation | PASS; no strategy |
| **376–385** | **Noncanonical research-input adoption, rollback, release harness and mandatory global suite** | **PASS; {decision}** |
| 386–395 | Observation-only stability and automated release-gate maturation | Planned, research-only |

Operational: `BLOCKED_RESEARCH_ONLY`. Capital: `R$ 0`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 376–385

- Phases completed: `376–385`
- Targeted tests: `{payload['targeted_tests']['tests']}`
- Global test files: `{full['test_file_count']}`
- Global tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Release harness pass: `{payload['release_harness_pass']}`
- Canonical data writes: `0`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""
    roadmap = f"""# QRDS Roadmap 386–395 — Research Only

## Entering decision

`{decision}`

## Recommended sequence

- **386:** freeze observation-only use cases for the noncanonical dataset.
- **387:** run schema-compatibility observation adapters without strategy metrics.
- **388:** compare repeated dataset integrity fingerprints over time without new collection.
- **389:** audit release-harness coverage against the frozen failure taxonomy.
- **390:** exercise clean-clone and interrupted-resume fixtures.
- **391:** validate the manual/pull-request GitHub release workflow configuration.
- **392–393:** no scientific family unless a new novelty and budget review is explicitly approved.
- **394:** update the unified portal.
- **395:** integrated checkpoint; the next mandatory global suite remains scheduled by tracking policy.

## Permanent prohibition

The noncanonical dataset cannot automatically replace canonical inputs, reopen closed families, create a signal, authorize allocation, connect a private account, place orders or use capital.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 385,
        "baseline_phase375_head": BASELINE_PHASE375_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "dataset_adoption": {
            "candidate_dataset_adopted_noncanonical": True,
            "candidate_dataset_adopted_canonical": False,
            "candidate_row_count": payload["candidate_row_count"],
            "raw_input_count": payload["raw_input_count"],
            "release_harness_pass": payload["release_harness_pass"],
            "canonical_data_writes": 0,
        },
        "global_full_suite": {
            "passed": full["passed"],
            "test_files": full["test_file_count"],
            "tests": full["totals"]["tests"],
            "failures": full["totals"]["failures"],
            "errors": full["totals"]["errors"],
            "manifest_stable": full["manifest_stable"],
        },
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 395,
        "next_mandatory_global_full_suite": 405,
        "roadmap_window": "386-395",
    }
    tracking_dir.mkdir(parents=True, exist_ok=True)
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE385.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE385.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE385.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_376_385.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_386_395_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase385.json", snapshot)


def build_checkpoint(
    paths: dict[int, Path],
    *,
    targeted_junit_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
    full_suite_output_dir: Path,
    per_file_timeout_seconds: int = 1800,
    full_suite_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = {phase: read_json(path) for phase, path in paths.items()}
    for phase, item in items.items():
        validate_phase(item, phase)
    p375 = items[375]
    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Targeted tests failed: {targeted}")
    checks = {
        "phase375_quality_contract_pass": p375.get("data_quality_contract_pass") is True,
        "phase376_result_registered": items[376].get("data_quality_contract_pass") is True,
        "phase377_noncanonical_adoption_approved": items[377].get("candidate_adoption_approved") is True,
        "phase377_canonical_adoption_forbidden": items[377].get("canonical_adoption_approved") is False,
        "phase378_closed_family_isolation_pass": items[378].get("isolation_pass") is True,
        "phase379_candidate_contract_frozen": items[379].get("candidate_contract_frozen") is True,
        "phase379_noncanonical_only": items[379].get("candidate_dataset_adopted_noncanonical") is True and items[379].get("candidate_dataset_adopted_canonical") is False,
        "phase380_synthetic_dry_run_pass": items[380].get("dry_run_pass") is True and int(items[380].get("real_rows_used", -1)) == 0,
        "phase381_integrity_pass": items[381].get("integrity_pass") is True,
        "phase382_rollback_ready": items[382].get("rollback_ready") is True and items[382].get("coexistence_pass") is True,
        "phase383_release_harness_pass": items[383].get("release_harness_pass") is True,
        "phase384_portal_ready": items[384].get("candidate_dataset_adopted_noncanonical") is True and items[384].get("capital_authorized_brl") == 0,
        "canonical_writes_zero_all_phases": all(int(items[phase].get("canonical_data_writes", items[phase].get("locks", {}).get("canonical_data_writes", -1))) == 0 for phase in range(376, 385)),
    }
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    if failed_checks:
        raise RuntimeError(f"Phase 376-384 integration checks failed; failed_checks={failed_checks!r}.")
    full = full_suite_override or run_resumable_full_suite(full_suite_output_dir, per_file_timeout_seconds=per_file_timeout_seconds)
    if not full.get("passed"):
        raise RuntimeError(f"Mandatory global full-suite failed: {full}")
    payload = base_payload(385, "NONCANONICAL_RESEARCH_DATASET_ADOPTION_FULL_INTEGRATION_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update({
        "gate": "PHASE385_NONCANONICAL_RESEARCH_DATASET_ADOPTION_FULL_INTEGRATION_CHECKPOINT_READY_RESEARCH_ONLY",
        "batch_gate": "PHASE376_385_NONCANONICAL_RESEARCH_DATASET_ADOPTION_CHECKPOINT_PASS_RESEARCH_ONLY",
        "baseline_phase375_head": BASELINE_PHASE375_HEAD,
        "phase_chain": {str(phase): {"gate": items[phase].get("gate"), "artifact_fingerprint": items[phase].get("artifact_fingerprint")} for phase in range(376, 385)},
        "integration_checks": checks,
        "integration_failed_checks": [],
        "manual_adoption_decision": items[377].get("selected_decision"),
        "candidate_dataset_adopted_noncanonical": True,
        "candidate_dataset_adopted_canonical": False,
        "candidate_contract_fingerprint": items[379].get("candidate_contract_fingerprint"),
        "candidate_row_count": int(items[381].get("candidate_row_count", 0)),
        "raw_input_count": int(items[382].get("raw_input_count", 0)),
        "rollback_ready": True,
        "release_harness_pass": True,
        "observed_failure_classes": items[383].get("observed_failure_classes", []),
        "github_release_workflow_installed": items[383].get("workflow_installed"),
        "github_release_workflow_trigger_mode": items[383].get("workflow_trigger_mode"),
        "canonical_data_writes": 0,
        "closed_families_reopened": False,
        "new_family_opened": False,
        "active_hypotheses": 0,
        "active_experiment_budget": 0,
        "public_collection_started": False,
        "targeted_tests": targeted,
        "global_full_suite": full,
        "current_portal_relative_path": items[384].get("portal_relative_path"),
        "next_window_decision": "NONCANONICAL_DATASET_OBSERVATION_AND_RELEASE_GATE_HARDENING_ONLY_RESEARCH_ONLY",
        "next_tracking_checkpoint": 395,
        "next_mandatory_global_full_suite": 405,
    })
    payload["artifact_fingerprint"] = fingerprint(payload)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(artifact_path, payload)
    write_summary(
        documentation_path,
        title="Phase 385 — Noncanonical Research-dataset Adoption Full Integration Checkpoint",
        gate=payload["gate"],
        bullets=[
            "Noncanonical adoption: `True`",
            "Canonical adoption: `False`",
            f"Candidate rows: `{payload['candidate_row_count']}`",
            f"Raw inputs preserved: `{payload['raw_input_count']}`",
            "Release harness pass: `True`",
            f"Global test files: `{full['test_file_count']}`",
            f"Global tests: `{full['totals']['tests']}`",
            f"Failures: `{full['totals']['failures']}`",
            f"Errors: `{full['totals']['errors']}`",
            "Canonical data writes: `0`",
            "Capital used: `R$ 0`",
        ],
    )
    _write_tracking(payload, tracking_dir)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    definitions = {
        375: "data_quality_remediation_integrated_checkpoint",
        376: "successful_data_quality_remediation_result_registry",
        377: "manual_noncanonical_research_input_adoption_review",
        378: "closed_family_isolation_audit",
        379: "noncanonical_research_dataset_schema_and_lineage_contract",
        380: "synthetic_noncanonical_adoption_dry_run",
        381: "noncanonical_research_dataset_integrity_audit",
        382: "rollback_and_raw_coexistence_audit",
        383: "release_harness_and_repetitive_failure_scanner",
        384: "noncanonical_research_dataset_adoption_portal",
    }
    for phase, slug in definitions.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=artifacts / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json")
    parser.add_argument("--targeted-junit", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, default=artifacts / "phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint_research_only" / "phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint.json")
    parser.add_argument("--documentation", type=Path, default=ROOT / "docs/reports/integration/phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint_summary.md")
    parser.add_argument("--tracking-dir", type=Path, default=ROOT / "docs/reports/project_tracking")
    parser.add_argument("--full-suite-output-dir", type=Path, default=artifacts / "phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint_research_only" / "full_suite")
    parser.add_argument("--per-file-timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    paths = {phase: getattr(args, f"phase{phase}_artifact") for phase in definitions}
    payload = build_checkpoint(paths, targeted_junit_path=args.targeted_junit, artifact_path=args.artifact, documentation_path=args.documentation, tracking_dir=args.tracking_dir, full_suite_output_dir=args.full_suite_output_dir, per_file_timeout_seconds=args.per_file_timeout_seconds)
    full = payload["global_full_suite"]
    print(payload["gate"])
    print("Global full-suite: PASS")
    print("Test files:", full["test_file_count"])
    print("Tests:", full["totals"]["tests"])
    print("Failures:", full["totals"]["failures"])
    print("Errors:", full["totals"]["errors"])
    print("Manifest stable:", full["manifest_stable"])
    print("Noncanonical dataset adopted:", payload["candidate_dataset_adopted_noncanonical"])
    print("Canonical dataset adopted:", payload["candidate_dataset_adopted_canonical"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
