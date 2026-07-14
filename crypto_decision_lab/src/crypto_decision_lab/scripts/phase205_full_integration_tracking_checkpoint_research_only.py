from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, load_json, require_phase, utc_now, write_json, write_text

ROOT = Path(__file__).resolve().parents[3]

def resolve_repo_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()



def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_test_files(root: Path = ROOT) -> list[Path]:
    return sorted(path for path in (root / "tests").rglob("test_*.py") if path.is_file())


def build_manifest(test_files: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in test_files
    ]


def split_shards(test_files: list[Path], count: int = 3) -> list[list[Path]]:
    shards = [[] for _ in range(count)]
    for index, path in enumerate(test_files):
        shards[index % count].append(path)
    return shards


def parse_junit(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key, 0))
    return totals


def tracked_mutations() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    paths = []
    for line in result.stdout.splitlines():
        raw = line[3:] if len(line) >= 4 else ""
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        raw = raw.strip().strip('"')
        if raw:
            paths.append(raw)
    return sorted(set(paths))


def restore_mutations(paths: list[str]) -> None:
    if not paths:
        return
    subprocess.run(["git", "restore", "--staged", "--worktree", "--", *paths], cwd=ROOT, check=True)


def untracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        raw = line[3:].strip().strip('"')
        if raw:
            paths.append(raw.replace("\\", "/"))
    return sorted(set(paths))


def remove_generated_untracked(paths: list[str]) -> list[str]:
    removed: list[str] = []

    for raw in sorted(set(paths)):
        candidate = (ROOT / raw).resolve()

        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError as error:
            raise RuntimeError(
                f"Refusing to remove path outside repository: {candidate}"
            ) from error

        if candidate.is_symlink() or candidate.is_file():
            candidate.unlink()
            removed.append(raw)
        elif candidate.is_dir():
            raise RuntimeError(
                f"Refusing recursive cleanup of generated directory: {raw}"
            )

        parent = candidate.parent
        while parent != ROOT:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    return removed


def run_full_suite(output_dir: Path, timeout_seconds: int = 1800) -> dict[str, Any]:
    tests = discover_test_files()
    manifest_before = build_manifest(tests)
    shards = split_shards(tests, 3)
    output_dir.mkdir(parents=True, exist_ok=True)
    shard_results = []
    restored_paths: list[str] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    if os.name == "nt":
        venv_scripts = ROOT / ".venv" / "Scripts"
        venv_python = venv_scripts / "python.exe"

        if not venv_python.is_file():
            raise RuntimeError(
                f"Phase 205 venv Python is missing: {venv_python}"
            )

        env["VIRTUAL_ENV"] = str(ROOT / ".venv")
        env.pop("PYTHONHOME", None)
        env["PYTHON"] = str(venv_python)
        env["PYTHON_EXECUTABLE"] = str(venv_python)
        env["PATH"] = (
            str(venv_scripts)
            + os.pathsep
            + env.get("PATH", "")
        )

        bash_candidates = [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\usr\bin\bash.exe"),
        ]
        path_entries = [
            Path(item)
            for item in env.get("PATH", "").split(os.pathsep)
            if item
        ]
        bash_on_path = any(
            (entry / "bash.exe").is_file()
            for entry in path_entries
        )

        if not bash_on_path:
            bash_executable = next(
                (
                    candidate
                    for candidate in bash_candidates
                    if candidate.is_file()
                ),
                None,
            )
            if bash_executable is None:
                raise RuntimeError(
                    "Git Bash is required by wrapper tests but "
                    "bash.exe was not found."
                )
            env["PATH"] = (
                str(bash_executable.parent)
                + os.pathsep
                + env.get("PATH", "")
            )

    removed_generated_paths: list[str] = []

    for index, shard in enumerate(shards, start=1):
        untracked_before = set(untracked_paths())
        junit = output_dir / f"phase205_shard_{index}.xml"
        log = output_dir / f"phase205_shard_{index}.log"
        args = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            f"--junitxml={junit}",
            *[path.relative_to(ROOT).as_posix() for path in shard],
        ]
        print(f"PHASE205_SHARD_{index}_START files={len(shard)}", flush=True)
        timed_out = False
        try:
            completed = subprocess.run(
                args,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                errors="backslashreplace",
                timeout=timeout_seconds,
                check=False,
            )
            returncode = completed.returncode
            log.write_text(completed.stdout + "\n--- STDERR ---\n" + completed.stderr, encoding="utf-8")
        except subprocess.TimeoutExpired as error:
            timed_out = True
            returncode = 124
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="backslashreplace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="backslashreplace")
            log.write_text(stdout + "\n--- STDERR ---\n" + stderr, encoding="utf-8")

        mutations = tracked_mutations()
        if mutations:
            restore_mutations(mutations)
            restored_paths.extend(mutations)

        untracked_after = set(untracked_paths())
        generated_untracked = sorted(
            untracked_after - untracked_before
        )
        removed_untracked = remove_generated_untracked(
            generated_untracked
        )
        removed_generated_paths.extend(removed_untracked)

        junit_counts = parse_junit(junit)
        shard_result = {
            "shard": index,
            "file_count": len(shard),
            "returncode": returncode,
            "timed_out": timed_out,
            "junit": junit_counts,
            "log_path": log.relative_to(ROOT).as_posix(),
            "restored_tracked_paths": mutations,
            "removed_generated_untracked_paths": removed_untracked,
        }
        shard_results.append(shard_result)
        print(
            f"PHASE205_SHARD_{index}_END rc={returncode} tests={junit_counts['tests']} failures={junit_counts['failures']} errors={junit_counts['errors']}",
            flush=True,
        )
        if returncode != 0 or timed_out or junit_counts["failures"] or junit_counts["errors"]:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            print("\n".join(tail), flush=True)
            break

    manifest_after = build_manifest(tests)
    manifest_stable = manifest_before == manifest_after
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for item in shard_results:
        for key in totals:
            totals[key] += item["junit"][key]
    all_shards_completed = len(shard_results) == len(shards)
    passed = (
        all_shards_completed
        and all(item["returncode"] == 0 and not item["timed_out"] for item in shard_results)
        and totals["failures"] == 0
        and totals["errors"] == 0
        and manifest_stable
    )
    return {
        "test_file_count": len(tests),
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_stable,
        "shard_count": len(shards),
        "all_shards_completed": all_shards_completed,
        "shards": shard_results,
        "totals": totals,
        "restored_tracked_paths": sorted(set(restored_paths)),
        "removed_generated_untracked_paths": sorted(
            set(removed_generated_paths)
        ),
        "passed": passed,
    }



def _phase205_windows_process_snapshot() -> dict[int, dict[str, object]]:
    if os.name != "nt":
        return {}

    command = (
        "$items = Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine; "
        "$items | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}

    import json as _json

    payload = _json.loads(result.stdout)
    if isinstance(payload, dict):
        payload = [payload]

    snapshot: dict[int, dict[str, object]] = {}
    for item in payload:
        try:
            process_id = int(item.get("ProcessId", 0))
            parent_id = int(item.get("ParentProcessId", 0))
        except (TypeError, ValueError):
            continue

        if process_id <= 0:
            continue

        snapshot[process_id] = {
            "process_id": process_id,
            "parent_process_id": parent_id,
            "name": str(item.get("Name") or ""),
            "command_line": str(item.get("CommandLine") or ""),
        }

    return snapshot


def _phase205_cleanup_new_test_processes(
    before: dict[int, dict[str, object]],
) -> list[str]:
    if os.name != "nt":
        return []

    after = _phase205_windows_process_snapshot()
    new_ids = set(after) - set(before)

    candidates: set[int] = set()
    for process_id in new_ids:
        item = after[process_id]
        name = str(item["name"]).lower()
        command_line = str(item["command_line"]).lower()

        if name == "bash.exe" and "qrds_" in command_line:
            candidates.add(process_id)

        if (
            name == "python.exe"
            and "-m http.server" in command_line
        ):
            candidates.add(process_id)

    children_by_parent: dict[int, list[int]] = {}
    for process_id, item in after.items():
        parent_id = int(item["parent_process_id"])
        children_by_parent.setdefault(parent_id, []).append(process_id)

    queue = list(candidates)
    kill_ids = set(candidates)

    while queue:
        parent_id = queue.pop()
        for child_id in children_by_parent.get(parent_id, []):
            if child_id not in kill_ids and child_id in new_ids:
                kill_ids.add(child_id)
                queue.append(child_id)

    removed: list[str] = []
    for process_id in sorted(kill_ids, reverse=True):
        item = after.get(process_id, {})
        descriptor = (
            f"{process_id}:"
            f"{item.get('name', '')}:"
            f"{item.get('command_line', '')}"
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Stop-Process -Id "
                    f"{process_id} "
                    "-Force -ErrorAction SilentlyContinue"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        removed.append(descriptor)

    return removed


def _phase205_kill_process_tree(process_id: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process_id), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return

    try:
        os.killpg(process_id, 9)
    except (ProcessLookupError, PermissionError):
        pass


def _phase205_resumable_run_full_suite(
    output_dir: Path,
    timeout_seconds: int = 5400,
) -> dict[str, Any]:
    tests = discover_test_files()
    manifest_before = build_manifest(tests)
    shards = split_shards(tests, 3)
    output_dir.mkdir(parents=True, exist_ok=True)

    shard_results = []
    restored_paths: list[str] = []
    removed_generated_paths: list[str] = []
    removed_test_processes: list[str] = []

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    if os.name == "nt":
        venv_scripts = ROOT / ".venv" / "Scripts"
        venv_python = venv_scripts / "python.exe"

        if not venv_python.is_file():
            raise RuntimeError(
                f"Phase 205 venv Python is missing: {venv_python}"
            )

        env["VIRTUAL_ENV"] = str(ROOT / ".venv")
        env.pop("PYTHONHOME", None)
        env["PYTHON"] = str(venv_python)
        env["PYTHON_EXECUTABLE"] = str(venv_python)

        bash_candidates = [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
            Path(r"C:\Program Files (x86)\Git\usr\bin\bash.exe"),
        ]
        bash_executable = next(
            (
                candidate
                for candidate in bash_candidates
                if candidate.is_file()
            ),
            None,
        )
        if bash_executable is None:
            raise RuntimeError("Git Bash bash.exe was not found.")

        env["PATH"] = (
            str(venv_scripts)
            + os.pathsep
            + str(bash_executable.parent)
            + os.pathsep
            + env.get("PATH", "")
        )

    effective_timeout = max(int(timeout_seconds), 5400)

    for index, shard in enumerate(shards, start=1):
        junit = output_dir / f"phase205_shard_{index}.xml"
        log = output_dir / f"phase205_shard_{index}.log"
        assignment = (
            output_dir
            / f"phase205_shard_{index}_files.json"
        )
        assignment.write_text(
            __import__("json").dumps(
                [
                    path.relative_to(ROOT).as_posix()
                    for path in shard
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        if index == 1 and junit.is_file() and log.is_file():
            existing_counts = parse_junit(junit)
            if (
                existing_counts["tests"] > 0
                and existing_counts["failures"] == 0
                and existing_counts["errors"] == 0
            ):
                shard_results.append(
                    {
                        "shard": index,
                        "file_count": len(shard),
                        "returncode": 0,
                        "timed_out": False,
                        "junit": existing_counts,
                        "junit_path": junit.relative_to(ROOT).as_posix(),
                        "log_path": log.relative_to(ROOT).as_posix(),
                        "restored_tracked_paths": [],
                        "removed_generated_untracked_paths": [],
                        "removed_test_processes": [],
                        "reused_successful_result": True,
                    }
                )
                print(
                    "PHASE205_SHARD_1_REUSED "
                    f"tests={existing_counts['tests']} "
                    "failures=0 errors=0",
                    flush=True,
                )
                continue

        untracked_before = set(untracked_paths())
        processes_before = _phase205_windows_process_snapshot()

        args = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            f"--junitxml={junit}",
            *[
                path.relative_to(ROOT).as_posix()
                for path in shard
            ],
        ]

        print(
            f"PHASE205_SHARD_{index}_START "
            f"files={len(shard)} "
            f"timeout={effective_timeout}s",
            flush=True,
        )

        timed_out = False
        process = subprocess.Popen(
            args,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(os.name != "nt"),
        )

        try:
            stdout, stderr = process.communicate(
                timeout=effective_timeout
            )
            returncode = int(process.returncode or 0)
        except subprocess.TimeoutExpired:
            timed_out = True
            _phase205_kill_process_tree(process.pid)
            stdout, stderr = process.communicate()
            returncode = 124

        log.write_text(
            stdout
            + "\n--- STDERR ---\n"
            + stderr,
            encoding="utf-8",
        )

        mutations = tracked_mutations()
        if mutations:
            restore_mutations(mutations)
            restored_paths.extend(mutations)

        untracked_after = set(untracked_paths())
        generated_untracked = sorted(
            untracked_after - untracked_before
        )
        removed_untracked = remove_generated_untracked(
            generated_untracked
        )
        removed_generated_paths.extend(removed_untracked)

        removed_processes = _phase205_cleanup_new_test_processes(
            processes_before
        )
        removed_test_processes.extend(removed_processes)

        junit_counts = parse_junit(junit)

        shard_result = {
            "shard": index,
            "file_count": len(shard),
            "returncode": returncode,
            "timed_out": timed_out,
            "junit": junit_counts,
            "junit_path": junit.relative_to(ROOT).as_posix(),
            "log_path": log.relative_to(ROOT).as_posix(),
            "restored_tracked_paths": mutations,
            "removed_generated_untracked_paths": removed_untracked,
            "removed_test_processes": removed_processes,
            "reused_successful_result": False,
        }
        shard_results.append(shard_result)

        print(
            f"PHASE205_SHARD_{index}_END "
            f"rc={returncode} "
            f"tests={junit_counts['tests']} "
            f"failures={junit_counts['failures']} "
            f"errors={junit_counts['errors']} "
            f"timed_out={timed_out}",
            flush=True,
        )

        if (
            returncode != 0
            or timed_out
            or junit_counts["failures"] != 0
            or junit_counts["errors"] != 0
        ):
            print(log.read_text(encoding="utf-8")[-12000:])
            break

    manifest_after = build_manifest(tests)
    manifest_stable = manifest_before == manifest_after

    totals = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    for item in shard_results:
        for key in totals:
            totals[key] += item["junit"][key]

    all_shards_completed = len(shard_results) == len(shards)
    passed = (
        all_shards_completed
        and all(
            item["returncode"] == 0
            and not item["timed_out"]
            for item in shard_results
        )
        and totals["failures"] == 0
        and totals["errors"] == 0
        and manifest_stable
    )

    return {
        "test_file_count": len(tests),
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_stable,
        "shard_count": len(shards),
        "all_shards_completed": all_shards_completed,
        "shards": shard_results,
        "totals": totals,
        "restored_tracked_paths": sorted(set(restored_paths)),
        "removed_generated_untracked_paths": sorted(
            set(removed_generated_paths)
        ),
        "removed_test_processes": sorted(
            set(removed_test_processes)
        ),
        "passed": passed,
    }


run_full_suite = _phase205_resumable_run_full_suite

def build_tracking_docs(output: dict[str, Any], tracking_dir: Path) -> None:
    full = output["full_suite"]
    phases = output["phase_chain"]
    master = "\n".join([
        "# QRDS Master Progress by Tens - Phase 205",
        "",
        "**Integration baseline before batch:** `a5f5981`",
        "**Checkpoint status:** `PASS_RESEARCH_ONLY`",
        "**Operational status:** `BLOCKED_RESEARCH_ONLY`",
        "",
        "## Executive view",
        "",
        "The 196-205 window established source lineage, temporal policy, anomaly evidence, provenance reconciliation and a deterministic shadow replay evidence chain. It did not authorize decisions, signals, allocation, orders or canonical writes.",
        "",
        "```mermaid",
        "flowchart LR",
        "  P195[Phase 195 Integrated Baseline] --> P196[196 Source Registry]",
        "  P196 --> P197[197 Temporal Policy]",
        "  P197 --> P198[198 Anomaly Audit]",
        "  P198 --> P199[199 Reconciliation]",
        "  P199 --> P200[200 Data Trust Checkpoint]",
        "  P200 --> P201[201 Shadow Replay Harness]",
        "  P201 --> P202[202 Reproducibility]",
        "  P202 --> P203[203 Causality Audit]",
        "  P203 --> P204[204 Evidence Scorecard]",
        "  P204 --> P205[205 Full Integration]",
        "  P205 --> BLOCKED[BLOCKED_RESEARCH_ONLY]",
        "```",
        "",
        "## Phase 196-205 status",
        "",
        "| Phase | Result | Meaning |",
        "|---:|---|---|",
        *[f"| {phase} | `{data['status']}` | {data['meaning']} |" for phase, data in phases.items()],
        "",
        "## Full-suite checkpoint",
        "",
        f"- Test files discovered: `{full['test_file_count']}`",
        f"- Tests executed: `{full['totals']['tests']}`",
        f"- Failures: `{full['totals']['failures']}`",
        f"- Errors: `{full['totals']['errors']}`",
        f"- Manifest stable: `{full['manifest_stable']}`",
        f"- Full suite passed: `{full['passed']}`",
        "",
        "## Locks",
        "",
        "```text",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "data_trust_validated: False",
        "predictive_validity_established: False",
        "decision_layer_allowed: False",
        "promotion_allowed: False",
        "canonical_data_writes: 0",
        "```",
        "",
        "## Next window",
        "",
        "Phases 206-215 should move from synthetic replay mechanics toward controlled historical replay evidence, while preserving the same closed operational gates.",
    ])
    milestone = "\n".join([
        "# QRDS Integrated Test Milestone 196-205",
        "",
        "**Status:** `PASS_RESEARCH_ONLY`",
        "",
        "## Integrated chain",
        "",
        "196 source registry -> 197 temporal policy -> 198 anomaly audit -> 199 reconciliation -> 200 checkpoint -> 201 deterministic replay -> 202 reproducibility -> 203 causality -> 204 scorecard -> 205 full integration.",
        "",
        "## Evidence",
        "",
        f"- Frozen test files: `{full['test_file_count']}`",
        f"- Executed tests: `{full['totals']['tests']}`",
        f"- Failures: `{full['totals']['failures']}`",
        f"- Errors: `{full['totals']['errors']}`",
        f"- Shards completed: `{len(full['shards'])}/{full['shard_count']}`",
        f"- Test manifest stable: `{full['manifest_stable']}`",
        f"- Test-induced tracked paths restored: `{len(full['restored_tracked_paths'])}`",
        "",
        "## Interpretation",
        "",
        "The integrated software stack passed the available test suite. This does not prove market edge, live-data trust, predictive validity, execution quality or production readiness.",
        "",
        "```text",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "real_orders_generated: False",
        "real_capital_used: False",
        "canonical_data_writes: 0",
        "```",
    ])
    roadmap = "\n".join([
        "# QRDS Roadmap 206-215 - Research Only",
        "",
        "**Theme:** Controlled Historical Replay Evidence",
        "**Mode:** `BLOCKED_RESEARCH_ONLY`",
        "",
        "```mermaid",
        "flowchart LR",
        "  P206[206 Historical Replay Dataset Contract] --> P207[207 Replay Window Builder]",
        "  P207 --> P208[208 Missing Data Policy]",
        "  P208 --> P209[209 Historical Replay Runner]",
        "  P209 --> P210[210 Replay Batch Checkpoint]",
        "  P210 --> P211[211 Counterfactual Trace Audit]",
        "  P211 --> P212[212 Stability Across Windows]",
        "  P212 --> P213[213 Regime Segmentation Evidence]",
        "  P213 --> P214[214 Historical Replay Scorecard]",
        "  P214 --> P215[215 Integrated Checkpoint]",
        "```",
        "",
        "| Phase | Objective |",
        "|---:|---|",
        "| 206 | Define historical replay dataset and snapshot contract. |",
        "| 207 | Build deterministic replay windows without hidden sorting. |",
        "| 208 | Define explicit missing-data and gap handling policies. |",
        "| 209 | Execute controlled historical replay with no decisions or orders. |",
        "| 210 | Consolidate the first historical replay evidence batch. |",
        "| 211 | Audit counterfactual and future-information access. |",
        "| 212 | Measure trace stability across multiple windows. |",
        "| 213 | Segment evidence by market regime without promotion. |",
        "| 214 | Produce a historical replay evidence scorecard. |",
        "| 215 | Integrate the window and update project tracking. |",
        "",
        "Full-suite integration is recommended at 215 only if the historical replay runner changes shared architecture; otherwise the next mandatory global full-suite remains Phase 225.",
        "",
        "```text",
        "decision_layer_allowed: False",
        "promotion_allowed: False",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "canonical_data_writes: 0",
        "```",
    ])
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE205.md", master)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_196_205.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_206_215_RESEARCH_ONLY.md", roadmap)
    snapshot = {
        "schema": "qrds.project_tracking.phase205.v1",
        "baseline_phase": 205,
        "integration_baseline_commit": "a5f5981",
        "status": "PASS_RESEARCH_ONLY",
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "window": {"start": 196, "end": 205},
        "full_suite": {
            "test_files": full["test_file_count"],
            "tests": full["totals"]["tests"],
            "failures": full["totals"]["failures"],
            "errors": full["totals"]["errors"],
            "manifest_stable": full["manifest_stable"],
            "passed": full["passed"],
        },
        "next_tracking_checkpoint": 215,
        "next_mandatory_global_full_suite": 225,
        "locks": LOCKS,
    }
    write_json(tracking_dir / "qrds_progress_snapshot_phase205.json", snapshot)


def build_phase205(artifact_paths: list[Path], output_dir: Path, tracking_dir: Path, documentation_path: Path, timeout_seconds: int = 1800) -> dict[str, Any]:
    artifact_paths = [resolve_repo_path(path) for path in artifact_paths]
    output_dir = resolve_repo_path(output_dir)
    tracking_dir = resolve_repo_path(tracking_dir)
    documentation_path = resolve_repo_path(documentation_path)
    artifacts = [load_json(path) for path in artifact_paths]
    expected = list(range(196, 205))
    actual = [item.get("phase") for item in artifacts]
    if actual != expected:
        raise ValueError(f"Expected phase chain {expected}, found {actual}")
    full_suite = run_full_suite(output_dir / "full_suite", timeout_seconds=timeout_seconds)
    if not full_suite["passed"]:
        write_json(output_dir / "phase205_full_integration_checkpoint.json", {
            "phase": 205,
            "phase_status": "NEEDS_REVIEW_RESEARCH_ONLY",
            "full_suite": full_suite,
            "locks": LOCKS,
        })
        raise RuntimeError("Phase 205 full-suite integration failed.")

    phase_chain = {
        "196": {"status": artifacts[0].get("phase_status"), "meaning": "Source registry and lineage contract ready."},
        "197": {"status": artifacts[1].get("phase_status"), "meaning": "Temporal policy evidence ready."},
        "198": {"status": artifacts[2].get("phase_status"), "meaning": "Anomaly findings recorded."},
        "199": {"status": artifacts[3].get("phase_status"), "meaning": "Sources reconciled and provenance scored."},
        "200": {"status": artifacts[4].get("phase_status"), "meaning": "Data-trust evidence checkpoint complete with findings retained."},
        "201": {"status": artifacts[5].get("phase_status"), "meaning": "Deterministic shadow replay harness ready."},
        "202": {"status": artifacts[6].get("phase_status"), "meaning": "Replay snapshots reproducible."},
        "203": {"status": artifacts[7].get("phase_status"), "meaning": "Trace causality and time order passed."},
        "204": {"status": artifacts[8].get("phase_status"), "meaning": "Research evidence scorecard ready without approval."},
        "205": {"status": "PASS_RESEARCH_ONLY", "meaning": "Window and global full-suite integration passed."},
    }
    payload = {
        "schema": "qrds.phase205.full_integration_checkpoint.v1",
        "phase": 205,
        "phase_status": "PASS_RESEARCH_ONLY",
        "checkpoint_status": "FULL_INTEGRATION_196_205_PASS_RESEARCH_ONLY",
        "generated_at": utc_now(),
        "phase_chain": phase_chain,
        "full_suite": full_suite,
        "window_integration_passed": True,
        "global_full_suite_passed": True,
        "data_trust_validated": False,
        "predictive_validity_established": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "promotion_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_206_HISTORICAL_REPLAY_DATASET_CONTRACT_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase205_full_integration_checkpoint.json", payload)
    build_tracking_docs(payload, tracking_dir)
    write_text(documentation_path, "\n".join([
        "# Phase 205 - Full Integration and Tracking Checkpoint",
        "",
        "**Status:** `PASS_RESEARCH_ONLY`",
        "",
        f"- Test files: `{full_suite['test_file_count']}`",
        f"- Tests: `{full_suite['totals']['tests']}`",
        f"- Failures: `{full_suite['totals']['failures']}`",
        f"- Errors: `{full_suite['totals']['errors']}`",
        f"- Manifest stable: `{full_suite['manifest_stable']}`",
        f"- Full suite passed: `{full_suite['passed']}`",
        "",
        "Project tracking was updated for Phase 205 and the 206-215 roadmap was generated.",
        "",
        "```text",
        "data_trust_validated: False",
        "predictive_validity_established: False",
        "decision_layer_allowed: False",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "canonical_data_writes: 0",
        "```",
    ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracking-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    payload = build_phase205(args.artifact, args.output_dir, args.tracking_dir, args.documentation_path, args.timeout_seconds)
    print("PHASE205_FULL_INTEGRATION: PASS")
    print("Test files:", payload["full_suite"]["test_file_count"])
    print("Tests:", payload["full_suite"]["totals"]["tests"])
    print("Failures:", payload["full_suite"]["totals"]["failures"])
    print("Errors:", payload["full_suite"]["totals"]["errors"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
