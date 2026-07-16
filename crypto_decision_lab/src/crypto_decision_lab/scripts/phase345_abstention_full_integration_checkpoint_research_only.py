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

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    BASELINE_PHASE335_HEAD,
    LOCKS,
    ROOT,
    base_payload,
    fingerprint,
    parse_junit,
    read_json,
    sha256_file,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import utc_now_iso

MIN_TEST_FILES = 574
MIN_TESTS = 1481

def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _test_manifest() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        if not path.is_file():
            continue
        records.append(
            {
                "path": _rel(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def _assign_shards(records: list[dict[str, Any]], count: int = 3) -> list[list[dict[str, Any]]]:
    shards: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    totals = [0] * count
    for record in sorted(records, key=lambda item: (-int(item["size_bytes"]), item["path"])):
        index = min(range(count), key=lambda item: (totals[item], item))
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
            path = path[len("crypto_decision_lab/") :]
        if status and status[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            path = parts[index].decode("utf-8", errors="surrogateescape").replace("\\", "/")
            if path.startswith("crypto_decision_lab/"):
                path = path[len("crypto_decision_lab/") :]
        output[path] = status
        index += 1
    return output


def _cleanup_test_side_effects(
    before: dict[str, str],
    protected_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    after = _git_status_paths()
    new_paths = sorted(set(after) - set(before))
    restored: list[str] = []
    removed: list[str] = []
    refused: list[str] = []
    generated_roots = (
        "artifacts/",
        "docs/reports/",
    )
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
            if not relative.startswith(generated_roots):
                refused.append(relative)
                continue
            if candidate.is_file() or candidate.is_symlink():
                candidate.unlink()
                removed.append(relative)
            elif candidate.is_dir():
                shutil.rmtree(candidate)
                removed.append(relative)
            continue
        result = subprocess.run(
            ["git", "checkout", "--", relative],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            restored.append(relative)
        else:
            refused.append(relative)
    if refused:
        raise RuntimeError(
            "Global-suite generated unexpected repository paths that were not automatically changed: "
            + ", ".join(refused)
        )
    return {
        "restored_tracked_paths": restored,
        "removed_generated_untracked_paths": removed,
        "refused_paths": refused,
    }


def _safe_name(relative: str) -> str:
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
    stem = Path(relative).stem[:80]
    return f"{stem}_{digest}"


def run_resumable_full_suite(
    output_dir: Path,
    *,
    per_file_timeout_seconds: int = 1800,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    junit_dir = output_dir / "junit"
    log_dir = output_dir / "logs"
    junit_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "phase345_full_suite_progress.json"

    manifest_before = _test_manifest()
    if len(manifest_before) < MIN_TEST_FILES:
        raise RuntimeError(
            f"Test inventory regression: expected at least {MIN_TEST_FILES}, found {len(manifest_before)}."
        )
    manifest_fingerprint = hashlib.sha256(
        json.dumps(manifest_before, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    shards = _assign_shards(manifest_before, 3)
    shard_by_path = {
        record["path"]: index
        for index, shard in enumerate(shards, start=1)
        for record in shard
    }

    existing: dict[str, Any] = {}
    if progress_path.is_file():
        try:
            loaded = read_json(progress_path)
            if loaded.get("manifest_fingerprint") == manifest_fingerprint:
                existing = dict(loaded.get("results", {}))
        except Exception:
            existing = {}

    baseline_status = _git_status_paths()
    protected_relative = _rel(output_dir).rstrip("/") + "/"
    results: dict[str, Any] = {}
    reused_count = 0
    executed_count = 0
    started = time.monotonic()

    for position, record in enumerate(manifest_before, start=1):
        relative = record["path"]
        cached = existing.get(relative)
        if (
            isinstance(cached, dict)
            and cached.get("sha256") == record["sha256"]
            and cached.get("status") == "PASS"
            and int(cached.get("returncode", 1)) == 0
            and not bool(cached.get("timed_out", False))
            and Path(str(cached.get("junit_path", ""))).is_file()
        ):
            try:
                cached_totals = _parse_junit(Path(cached["junit_path"]))
            except Exception:
                cached_totals = None
            if cached_totals and cached_totals["failures"] == 0 and cached_totals["errors"] == 0:
                item = dict(cached)
                item["reused"] = True
                item["junit"] = cached_totals
                results[relative] = item
                reused_count += 1
                print(f"[{position}/{len(manifest_before)}] REUSE PASS {relative}", flush=True)
                continue

        name = _safe_name(relative)
        junit_path = junit_dir / f"{name}.xml"
        log_path = log_dir / f"{name}.log"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            f"--junitxml={junit_path}",
            str(ROOT / relative),
        ]
        print(f"[{position}/{len(manifest_before)}] RUN shard {shard_by_path[relative]} {relative}", flush=True)
        file_started = time.monotonic()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=per_file_timeout_seconds,
                check=False,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")

        duration = time.monotonic() - file_started
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nRETURN_CODE: {returncode}\nTIMED_OUT: {timed_out}\n"
            f"DURATION_SECONDS: {duration:.3f}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
            encoding="utf-8",
        )
        junit_totals = (
            _parse_junit(junit_path)
            if junit_path.is_file()
            else {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
        )
        passed = (
            returncode == 0
            and not timed_out
            and junit_totals["failures"] == 0
            and junit_totals["errors"] == 0
        )
        item = {
            "path": relative,
            "sha256": record["sha256"],
            "shard": shard_by_path[relative],
            "status": "PASS" if passed else "FAIL",
            "returncode": returncode,
            "timed_out": timed_out,
            "duration_seconds": duration,
            "junit_path": str(junit_path),
            "log_path": str(log_path),
            "junit": junit_totals,
            "reused": False,
        }
        results[relative] = item
        executed_count += 1
        write_json(
            progress_path,
            {
                "phase": 345,
                "manifest_fingerprint": manifest_fingerprint,
                "updated_at_utc": utc_now_iso(),
                "test_file_count": len(manifest_before),
                "results": results,
            },
        )
        if not passed:
            cleanup = _cleanup_test_side_effects(baseline_status, (protected_relative,))
            raise RuntimeError(
                f"Global-suite failure in {relative}. Classification: TEST_OR_FIXTURE_FAILURE, not strategy failure. "
                f"Return code={returncode}, timed_out={timed_out}, junit={junit_totals}, log={log_path}, cleanup={cleanup}"
            )

    cleanup = _cleanup_test_side_effects(baseline_status, (protected_relative,))
    manifest_after = _test_manifest()
    manifest_stable = manifest_before == manifest_after
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for item in results.values():
        for key in totals:
            totals[key] += int(item["junit"][key])
    all_passed = (
        len(results) == len(manifest_before)
        and all(item["status"] == "PASS" for item in results.values())
        and totals["failures"] == 0
        and totals["errors"] == 0
        and totals["tests"] >= MIN_TESTS
        and manifest_stable
    )
    return {
        "mode": "RESUMABLE_FILEWISE_THREE_SHARD_MANIFEST",
        "started_at_utc": utc_now_iso(),
        "duration_seconds": time.monotonic() - started,
        "per_file_timeout_seconds": per_file_timeout_seconds,
        "test_file_count": len(manifest_before),
        "minimum_test_file_count": MIN_TEST_FILES,
        "minimum_tests": MIN_TESTS,
        "manifest_fingerprint": manifest_fingerprint,
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_stable,
        "shard_count": 3,
        "shards": [
            {
                "shard": index,
                "file_count": len(shard),
                "total_bytes": sum(int(record["size_bytes"]) for record in shard),
                "files": [record["path"] for record in shard],
            }
            for index, shard in enumerate(shards, start=1)
        ],
        "reused_file_count": reused_count,
        "executed_file_count": executed_count,
        "all_files_completed": len(results) == len(manifest_before),
        "totals": totals,
        "cleanup": cleanup,
        "passed": all_passed,
    }



def _validate_phase_payload(payload: dict[str, Any], phase: int) -> None:
    validate_phase(payload, phase)
    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["action_status"] == "NO_ACTION_RESEARCH_ONLY"
    assert locks["decision_layer_allowed"] is False
    assert locks["canonical_data_writes"] == 0
    assert locks["position_size"] == 0
    assert locks["capital_used"] == 0
    assert locks["real_orders_created"] == 0


def _write_tracking(payload: dict[str, Any], tracking_dir: Path) -> None:
    full = payload["global_full_suite"]
    candidate = payload.get("historical_research_candidate_id")
    decision = payload["next_window_decision"]
    top = payload.get("top_diagnostic_metrics") or {}
    master = f"""# QRDS Master Progress by Tens — Phase 345

## Executive state

- Window completed: `336–345`
- Finite registry opened once: `True`
- Sealed templates evaluated: `{payload['template_count']}`
- Historical research candidate: `{candidate or 'NONE'}`
- Family decision: `{payload['family_decision']}`
- Strategy approved: `False`
- Forward shadow eligible: `False`
- Capital used: `R$ 0`
- Operational: `BLOCKED_RESEARCH_ONLY`

## Plain-language result

The project evaluated whether cross-exchange disagreement and data-quality
signals can identify periods when directional research should abstain. The
result is non-directional and cannot create buy, sell, allocation or order
instructions. With R$10.000 available, authorized capital remains `R$ 0`.

## Global validation

- Test files: `{full['test_file_count']}`
- Tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 345

```mermaid
flowchart TD
    A[Question and target frozen] --> B[12 sealed templates opened once]
    B --> C[As-of features]
    C --> D[H8 target components]
    D --> E[Nested walk-forward]
    E --> F[Holm + calibration + null]
    F --> G[Regime/provider/missingness robustness]
    G --> H[Coverage vs reliability]
    H --> I{{All gates pass?}}
    I -->|No| J[Close family as negative evidence]
    I -->|Yes| K[Historical research candidate only]
    J --> L[NO_ACTION_RESEARCH_ONLY]
    K --> L
    L --> M[No automatic freeze, forward, paper or capital]
```

**VOCE ESTA AQUI:** `{decision}`. Capital authorized: `R$ 0`.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 345

| Range | Dominant delivery | State |
|---|---|---|
| 0–325 | Foundation, public data, finite directional search and negative-evidence controls | Complete; no approved strategy |
| 326–335 | Manual preregistration, target freeze and sealed templates | Complete; registry remained closed |
| **336–345** | **One-time registry opening, historical non-directional evaluation, visual portal and mandatory global suite** | **PASS; {decision}** |
| 346–355 | Candidate-freeze review if eligible, otherwise negative-evidence closure and next-question governance | Planned, research-only |

Strategy approved: `False`. Capital used: `R$ 0`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 336–345

- Window phases completed: `336–345`
- Targeted tests: `{payload['targeted_tests']['tests']}`
- Global test files: `{full['test_file_count']}`
- Global tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Templates evaluated: `{payload['template_count']}`
- Holm survivors: `{payload['holm_survivor_count']}`
- Robust templates: `{payload['robust_template_count']}`
- Final eligible templates: `{payload['eligible_template_count']}`
- Historical research candidate: `{candidate or 'NONE'}`
- Candidate freeze created: `False`
- Forward evidence clock started: `False`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""
    if candidate:
        roadmap_body = f"""## Candidate-review path

- 346: immutable manual review package for historical candidate `{candidate}`.
- 347: verify candidate lineage, hashes and exact frozen behavior.
- 348: decide whether a candidate freeze may be created; no automatic freeze.
- 349: define a forward-only observation contract with zero historical credit.
- 350–352: dry-run monitoring and kill-switch contracts using fixtures only.
- 353–354: visual readiness portal and human review.
- 355: integrated checkpoint; forward shadow still requires a separate explicit gate.
"""
    else:
        roadmap_body = """## No-survivor path

- 346: register the abstention family as negative evidence.
- 347: block exact and semantic retests of the 12 templates.
- 348–350: audit failure causes and data limitations without parameter rescue.
- 351–352: decide whether data remediation or a genuinely new question is justified.
- 353–354: visual closure portal and research roadmap.
- 355: integrated checkpoint retaining `NO_ACTION_RESEARCH_ONLY`.
"""
    roadmap = f"""# QRDS Roadmap 346–355 — Research Only

## Entering decision

`{decision}`

{roadmap_body}

## Permanent prohibition

No recommendation, allocation, directional signal, order, private account
connection or capital use. A historical abstention result cannot automatically
create a candidate freeze, forward clock, paper trading or real execution.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 345,
        "baseline_phase335_head": BASELINE_PHASE335_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "global_full_suite": {
            "passed": full["passed"],
            "test_files": full["test_file_count"],
            "tests": full["totals"]["tests"],
            "failures": full["totals"]["failures"],
            "errors": full["totals"]["errors"],
            "manifest_stable": full["manifest_stable"],
        },
        "abstention_evaluation": {
            "template_count": payload["template_count"],
            "holm_survivor_count": payload["holm_survivor_count"],
            "robust_template_count": payload["robust_template_count"],
            "eligible_template_count": payload["eligible_template_count"],
            "historical_research_candidate_id": candidate,
            "family_decision": payload["family_decision"],
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
        },
        "top_diagnostic_metrics": top,
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 355,
        "next_mandatory_global_full_suite": 365,
        "roadmap_window": "346-355",
    }
    tracking_dir.mkdir(parents=True, exist_ok=True)
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE345.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE345.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE345.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_336_345.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_346_355_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase345.json", snapshot)


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
        _validate_phase_payload(item, phase)
    if items[335].get("next_window_decision") != "FINITE_REGISTRY_OPENING_ELIGIBLE_NEXT_WINDOW_RESEARCH_ONLY":
        raise RuntimeError("Phase 335 did not authorize finite registry opening.")
    if items[336].get("active_template_count") != 12:
        raise RuntimeError("Phase 336 did not open exactly 12 templates.")
    if items[339].get("historical_experiments_executed") != 12:
        raise RuntimeError("Phase 339 did not execute exactly 12 preregistered experiments.")
    if items[343].get("registry_open") is not False or items[343].get("experiment_budget_open") is not False:
        raise RuntimeError("Phase 343 did not close the one-time registry and budget.")
    if items[344].get("capital_authorized_brl") != 0:
        raise RuntimeError("Phase 344 portal authorized capital.")

    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Targeted tests failed: {targeted}")
    full_suite = full_suite_override or run_resumable_full_suite(
        full_suite_output_dir,
        per_file_timeout_seconds=per_file_timeout_seconds,
    )
    if not full_suite.get("passed"):
        raise RuntimeError(f"Mandatory global full-suite failed: {full_suite}")

    candidate = items[343].get("historical_research_candidate_id")
    decision = (
        "MANUAL_HISTORICAL_CANDIDATE_FREEZE_REVIEW_ONLY_RESEARCH_ONLY"
        if candidate
        else "ABSTENTION_FAMILY_CLOSED_NO_SURVIVOR_RESEARCH_ONLY"
    )
    payload = base_payload(345, "ABSTENTION_FULL_INTEGRATION_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE345_ABSTENTION_FULL_INTEGRATION_CHECKPOINT_READY_RESEARCH_ONLY",
            "batch_gate": "PHASE336_345_ABSTENTION_EVALUATION_CHECKPOINT_PASS_RESEARCH_ONLY",
            "baseline_phase335_head": BASELINE_PHASE335_HEAD,
            "phase_chain": {
                str(phase): {
                    "gate": items[phase].get("gate"),
                    "artifact_fingerprint": items[phase].get("artifact_fingerprint"),
                }
                for phase in range(336, 345)
            },
            "targeted_tests": targeted,
            "global_full_suite": full_suite,
            "template_count": items[336]["active_template_count"],
            "historical_rows": items[337]["row_count"],
            "fold_count": items[339]["fold_count"],
            "holm_survivor_count": items[340]["survivor_count"],
            "robust_template_count": items[341]["robust_template_count"],
            "eligible_template_count": items[343]["eligible_template_count"],
            "historical_research_candidate_id": candidate,
            "family_decision": items[343]["family_decision"],
            "top_diagnostic_template_id": items[340].get("top_diagnostic_template_id"),
            "top_diagnostic_metrics": items[340].get("top_diagnostic_metrics"),
            "next_window_decision": decision,
            "registry_open": False,
            "experiment_budget_open": False,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "forward_evidence_credit": 0,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "strategy_approved": False,
            "next_tracking_checkpoint": 355,
            "next_mandatory_global_full_suite": 365,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(artifact_path, payload)
    write_summary(
        documentation_path,
        title="Phase 345 — Abstention Full Integration Checkpoint",
        gate=payload["gate"],
        bullets=[
            f"Global test files: `{full_suite['test_file_count']}`",
            f"Global tests: `{full_suite['totals']['tests']}`",
            f"Holm survivors: `{payload['holm_survivor_count']}`",
            f"Final eligible templates: `{payload['eligible_template_count']}`",
            f"Historical research candidate: `{candidate or 'NONE'}`",
            f"Next-window decision: `{decision}`",
            "Candidate freeze created: `False`",
            "Strategy approved: `False`",
            "Capital used: `R$ 0`",
        ],
    )
    _write_tracking(payload, tracking_dir)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        335: artifacts / "phase335_preregistration_sealed_registry_checkpoint_research_only/phase335_preregistration_sealed_registry_checkpoint.json",
        336: artifacts / "phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json",
        337: artifacts / "phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json",
        338: artifacts / "phase338_frozen_h8_target_builder_research_only/phase338_frozen_h8_target_builder.json",
        339: artifacts / "phase339_nested_walk_forward_abstention_research_only/phase339_nested_walk_forward_abstention.json",
        340: artifacts / "phase340_holm_calibration_null_comparison_research_only/phase340_holm_calibration_null_comparison.json",
        341: artifacts / "phase341_regime_provider_missingness_robustness_research_only/phase341_regime_provider_missingness_robustness.json",
        342: artifacts / "phase342_abstention_coverage_reliability_tradeoff_research_only/phase342_abstention_coverage_reliability_tradeoff.json",
        343: artifacts / "phase343_research_candidate_eligibility_research_only/phase343_research_candidate_eligibility.json",
        344: artifacts / "phase344_abstention_visual_interpretation_portal_research_only/phase344_abstention_visual_interpretation_portal.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument("--targeted-junit", type=Path, required=True)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=artifacts / "phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json",
    )
    parser.add_argument(
        "--documentation",
        type=Path,
        default=ROOT / "docs/reports/integration/phase345_abstention_full_integration_checkpoint_summary.md",
    )
    parser.add_argument(
        "--tracking-dir",
        type=Path,
        default=ROOT / "docs/reports/project_tracking",
    )
    parser.add_argument(
        "--full-suite-output-dir",
        type=Path,
        default=artifacts / "phase345_abstention_full_integration_checkpoint_research_only/full_suite",
    )
    parser.add_argument("--per-file-timeout-seconds", type=int, default=1800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = {
        phase: getattr(args, f"phase{phase}_artifact")
        for phase in range(335, 345)
    }
    payload = build_checkpoint(
        paths,
        targeted_junit_path=args.targeted_junit,
        artifact_path=args.artifact,
        documentation_path=args.documentation,
        tracking_dir=args.tracking_dir,
        full_suite_output_dir=args.full_suite_output_dir,
        per_file_timeout_seconds=args.per_file_timeout_seconds,
    )
    full = payload["global_full_suite"]
    print(payload["gate"])
    print("Global full-suite: PASS")
    print("Test files:", full["test_file_count"])
    print("Tests:", full["totals"]["tests"])
    print("Failures:", full["totals"]["failures"])
    print("Errors:", full["totals"]["errors"])
    print("Manifest stable:", full["manifest_stable"])
    print("Historical research candidate:", payload["historical_research_candidate_id"])
    print("Next-window decision:", payload["next_window_decision"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
