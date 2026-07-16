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

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    LOCKS,
    ROOT,
    base_payload,
    read_json,
    sha256_file,
    utc_now_iso,
    validate_locks,
    write_json,
    write_text,
)

from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import fingerprint, parse_junit

BASELINE_PHASE315_HEAD = "4d45d3cf996da58ec1bba2a287bbf3b5ee3ce9bc"
MIN_TEST_FILES = 554
MIN_TESTS = 1461


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
    progress_path = output_dir / "phase325_full_suite_progress.json"

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
                "phase": 325,
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
    assert payload["phase"] == phase
    validate_locks(payload["locks"])
    assert payload["valid_for_decision"] is False
    assert payload["historical_result_authorizes_execution"] is False



def _write_tracking(payload: dict[str, Any], phase304: dict[str, Any], tracking_dir: Path) -> None:
    full = payload["global_full_suite"]
    decision = payload["next_window_decision"]
    mean_brl = float(phase304.get("outer_metrics_10bps", {}).get("mean_per_10000_brl", 0.0))
    lower_brl = float(phase304.get("outer_metrics_10bps", {}).get("lower_95_per_10000_brl", 0.0))
    master = f"""# QRDS/QOS/GATE BTC — Master Progress Phase 325

## Estado executivo

- Framework readiness: `100/100`
- Evidence readiness: `0/100`
- Operational readiness: `0/100`
- Current directional family: `CLOSED_NEGATIVE_RESULT_REGISTERED`
- New-family decision: `{decision}`
- New family opened: `False`
- Hypotheses registered in new family: `0`
- Experiment budget opened: `False`
- Strategy approved: `False`
- Forward shadow started: `False`
- Paper trading started: `False`
- Capital used: `R$ 0`
- Action: `NO_ACTION_RESEARCH_ONLY`

## Tradução para R$10.000

A família encerrada registrou média modelada de `R$ {mean_brl:.2f}` e limite
inferior de 95% de `R$ {lower_brl:.2f}` por R$10.000. A janela 316–325 não
procurou recuperar esse resultado; ela impediu reciclagem silenciosa e avaliou
se existe uma pergunta científica realmente diferente.

## Testes

- Global full-suite: `PASS`
- Test files: `{full['test_file_count']}`
- Tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Next tracking checkpoint: `335`
- Next mandatory global full-suite: `345`
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 325

```mermaid
flowchart TD
    A[24 directional hypotheses] --> B[Negative result registered]
    B --> C[Exact and semantic retests blocked]
    C --> D[Failure atlas]
    D --> E[Data coverage audit]
    E --> F[Exchange disagreement audit]
    F --> G[Derivatives missingness audit]
    G --> H{{Genuinely different question?}}
    H -->|No| I[No new family justified]
    H -->|Yes| J[Manual preregistration review only]
    I --> K[NO_ACTION_RESEARCH_ONLY]
    J --> K
    K --> L[New family unopened; budget zero]
    L --> M[Forward, paper and capital blocked]
```

**VOCE ESTA AQUI:** `{decision}`. Nenhuma família nova foi aberta.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 325

| Range | Dominant delivery | State |
|---|---|---|
| 0–305 | Foundation, public data, finite search and global validation | Complete; no approved edge |
| 306–315 | Stability diagnosis and candidate eligibility | Complete; current family closed |
| **316–325** | **Negative-evidence registry, anti-retest controls, data-quality audits, new-question preregistration decision, global suite** | **PASS; {decision}** |
| 326–335 | Conditional manual review or data remediation; no automatic family opening | Planned, research-only |

New family opened: `False`. Experiment budget opened: `False`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 316–325

- Window phases completed: `316–325`
- Global test files: `{full['test_file_count']}`
- Global tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Negative result registered: `True`
- Retest signatures blocked: `{payload['prohibited_signature_count']}`
- New scientific question justified: `{payload['genuinely_different_question_justified']}`
- Preregistration draft created: `{payload['preregistration_draft_created']}`
- New family opened: `False`
- Experiment budget opened: `False`
- Strategy approved: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Capital used: `R$ 0`
"""
    roadmap = f"""# QRDS Roadmap 326–335 — Research Only

## Entering decision

`{decision}`

## If manual preregistration review is allowed

- 326: human-readable novelty and non-overlap review package.
- 327: manual accept/reject contract for the scientific question only.
- 328–329: freeze the family definition and target; still zero hypotheses.
- 330–332: define a finite hypothesis budget only after explicit review.
- 333–334: software dry-run with synthetic fixtures; no historical evaluation.
- 335: integrated checkpoint deciding whether the finite registry may be opened.

## If the question was not justified

- 326–332: data remediation and missingness investigation only.
- 333–334: repeat quality audit without creating hypotheses.
- 335: checkpoint retaining `NO_ACTION_RESEARCH_ONLY`.

## Permanent prohibition

No recommendation, allocation, directional signal, order, account connection or
capital use. No automatic opening of a new family and no historical backfill to
the forward evidence clock.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 325,
        "baseline_phase315_head": BASELINE_PHASE315_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "global_full_suite": {
            "passed": full["passed"], "test_files": full["test_file_count"],
            "tests": full["totals"]["tests"], "failures": full["totals"]["failures"],
            "errors": full["totals"]["errors"], "manifest_stable": full["manifest_stable"],
        },
        "negative_evidence": {
            "current_family_closed": True,
            "negative_result_registered": True,
            "prohibited_signature_count": payload["prohibited_signature_count"],
        },
        "next_family": {
            "genuinely_different_question_justified": payload["genuinely_different_question_justified"],
            "preregistration_draft_created": payload["preregistration_draft_created"],
            "new_family_opened": False,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "decision": decision,
        },
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 335,
        "next_mandatory_global_full_suite": 345,
        "roadmap_window": "326-335",
    }
    tracking_dir.mkdir(parents=True, exist_ok=True)
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE325.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE325.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE325.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_316_325.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_326_335_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase325.json", snapshot)


def build_checkpoint(
    *,
    phase304_path: Path,
    phase315_path: Path,
    phase316_path: Path,
    phase317_path: Path,
    phase318_path: Path,
    phase319_path: Path,
    phase320_path: Path,
    phase321_path: Path,
    phase322_path: Path,
    phase323_path: Path,
    phase324_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
    full_suite_output_dir: Path,
    targeted_junit_path: Path,
    per_file_timeout_seconds: int = 1800,
) -> dict[str, Any]:
    paths = {
        304: phase304_path, 315: phase315_path, 316: phase316_path, 317: phase317_path,
        318: phase318_path, 319: phase319_path, 320: phase320_path, 321: phase321_path,
        322: phase322_path, 323: phase323_path, 324: phase324_path,
    }
    payloads: dict[int, dict[str, Any]] = {}
    for phase, path in paths.items():
        item = read_json(path)
        _validate_phase_payload(item, phase)
        payloads[phase] = item
    if payloads[315].get("current_family_decision") != "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY":
        raise RuntimeError("Phase 315 did not close the current family.")
    if payloads[316].get("negative_result_registered") is not True:
        raise RuntimeError("Negative evidence was not registered.")
    if payloads[317].get("prohibited_signature_count") != 24:
        raise RuntimeError("All 24 closed hypotheses must be blocked from silent retest.")
    if payloads[323].get("new_family_opened") is not False or payloads[323].get("experiment_budget_opened") is not False:
        raise RuntimeError("Phase 323 opened a family or budget automatically.")
    if payloads[324].get("new_family_opened") is not False:
        raise RuntimeError("Phase 324 portal claims a new family was opened.")

    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Batch 316-325 targeted tests did not pass: {targeted}")

    full_suite = run_resumable_full_suite(full_suite_output_dir, per_file_timeout_seconds=per_file_timeout_seconds)
    if not full_suite["passed"]:
        raise RuntimeError(f"Mandatory global full-suite did not pass: {full_suite}")

    draft = bool(payloads[323].get("preregistration_draft_created"))
    decision = "MANUAL_PREREGISTRATION_REVIEW_ONLY_RESEARCH_ONLY" if draft else "NO_NEW_FAMILY_JUSTIFIED_RESEARCH_ONLY"
    payload = base_payload(325, "NEGATIVE_EVIDENCE_AND_NEW_QUESTION_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update({
        "gate": "PHASE325_NEGATIVE_EVIDENCE_NEW_QUESTION_FULL_INTEGRATION_READY_RESEARCH_ONLY",
        "batch_gate": "PHASE316_325_NEGATIVE_EVIDENCE_NEW_QUESTION_CHECKPOINT_PASS_RESEARCH_ONLY",
        "baseline_phase315_head": BASELINE_PHASE315_HEAD,
        "phase_chain": {str(phase): {"gate": payloads[phase].get("gate"), "artifact_fingerprint": payloads[phase].get("artifact_fingerprint")} for phase in range(316, 325)},
        "targeted_tests": targeted,
        "global_full_suite": full_suite,
        "current_family_closed": True,
        "negative_result_registered": True,
        "prohibited_signature_count": payloads[317]["prohibited_signature_count"],
        "failure_category_count": payloads[318]["failure_category_count"],
        "coverage_audit_pass": payloads[319]["coverage_audit_pass"],
        "disagreement_context_available": payloads[320]["disagreement_context_available"],
        "derivatives_context_usable": payloads[321]["derivatives_context_usable"],
        "genuinely_different_question_justified": payloads[322]["genuinely_different_question_justified"],
        "preregistration_draft_created": draft,
        "next_window_decision": decision,
        "new_family_opened": False,
        "hypotheses_registered": 0,
        "experiment_budget_opened": False,
        "strategy_approved": False,
        "forward_shadow_eligible": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
        "forward_evidence_credit": 0,
        "historical_backfill_to_forward_clock": False,
        "next_tracking_checkpoint": 335,
        "next_mandatory_global_full_suite": 345,
    })
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(artifact_path, payload)
    _write_tracking(payload, payloads[304], tracking_dir)
    write_text(documentation_path, f"""# Phase 325 — Negative Evidence and New-Question Full Integration Checkpoint

Gate: `{payload['gate']}`  
Batch gate: `{payload['batch_gate']}`

- Global full-suite: `PASS`
- Test files: `{full_suite['test_file_count']}`
- Tests: `{full_suite['totals']['tests']}`
- Failures: `{full_suite['totals']['failures']}`
- Errors: `{full_suite['totals']['errors']}`
- Manifest stable: `{full_suite['manifest_stable']}`
- Current family closed: `True`
- Retest signatures blocked: `{payload['prohibited_signature_count']}`
- New scientific question justified: `{payload['genuinely_different_question_justified']}`
- Preregistration draft created: `{payload['preregistration_draft_created']}`
- New family opened: `False`
- Experiment budget opened: `False`
- Strategy approved: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`
- Capital used: `R$ 0`

The checkpoint validates software, lineage, negative-evidence controls and the
conditional preregistration decision. It does not validate a tradable edge.
""")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(); artifacts = ROOT / "artifacts"
    defaults = {
        304: artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",
        315: artifacts / "phase315_stability_family_checkpoint_research_only/phase315_stability_family_checkpoint.json",
        316: artifacts / "phase316_negative_evidence_registry_research_only/phase316_negative_evidence_registry.json",
        317: artifacts / "phase317_prohibited_retest_signature_registry_research_only/phase317_prohibited_retest_signature_registry.json",
        318: artifacts / "phase318_failure_atlas_research_only/phase318_failure_atlas.json",
        319: artifacts / "phase319_data_coverage_audit_v2_research_only/phase319_data_coverage_audit_v2.json",
        320: artifacts / "phase320_exchange_disagreement_audit_research_only/phase320_exchange_disagreement_audit.json",
        321: artifacts / "phase321_derivatives_missingness_audit_research_only/phase321_derivatives_missingness_audit.json",
        322: artifacts / "phase322_new_scientific_question_novelty_audit_research_only/phase322_new_scientific_question_novelty_audit.json",
        323: artifacts / "phase323_new_family_preregistration_contract_research_only/phase323_new_family_preregistration_contract.json",
        324: artifacts / "phase324_scientific_next_family_decision_portal_research_only/phase324_scientific_next_family_decision_portal.json",
    }
    for phase, path in defaults.items(): parser.add_argument(f"--phase{phase}-artifact", type=Path, default=path)
    parser.add_argument("--targeted-junit", type=Path, default=artifacts / "phase325_negative_evidence_new_question_full_integration_checkpoint_research_only/targeted_batch316_325.xml")
    parser.add_argument("--artifact", type=Path, default=artifacts / "phase325_negative_evidence_new_question_full_integration_checkpoint_research_only/phase325_negative_evidence_new_question_full_integration_checkpoint.json")
    parser.add_argument("--documentation", type=Path, default=ROOT / "docs/reports/integration/phase325_negative_evidence_new_question_full_integration_checkpoint_summary.md")
    parser.add_argument("--tracking-dir", type=Path, default=ROOT / "docs/reports/project_tracking")
    parser.add_argument("--full-suite-output-dir", type=Path, default=artifacts / "phase325_negative_evidence_new_question_full_integration_checkpoint_research_only/full_suite")
    parser.add_argument("--per-file-timeout-seconds", type=int, default=1800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_checkpoint(
        **{f"phase{phase}_path": getattr(args, f"phase{phase}_artifact") for phase in (304,315,316,317,318,319,320,321,322,323,324)},
        artifact_path=args.artifact, documentation_path=args.documentation, tracking_dir=args.tracking_dir,
        full_suite_output_dir=args.full_suite_output_dir, targeted_junit_path=args.targeted_junit, per_file_timeout_seconds=args.per_file_timeout_seconds,
    )
    full=payload["global_full_suite"]
    print(payload["gate"]); print(payload["batch_gate"]); print("Global full-suite: PASS"); print("Test files:",full["test_file_count"]); print("Tests:",full["totals"]["tests"]); print("Failures:",full["totals"]["failures"]); print("Errors:",full["totals"]["errors"]); print("Manifest stable:",full["manifest_stable"]); print("Next-window decision:",payload["next_window_decision"]); print("New family opened:",payload["new_family_opened"]); print("Strategy approved:",payload["strategy_approved"]); print("Operational:",payload["locks"]["operational_status"]); print("Action:",payload["locks"]["action_status"]); return 0

if __name__ == "__main__": raise SystemExit(main())
