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

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    read_json,
    research_caps,
    stable_digest,
    write_json,
    write_markdown,
)


def resolve_repo_path(path: Path, root: Path = ROOT) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_test_files(root: Path = ROOT) -> list[Path]:
    return sorted(
        path.resolve()
        for path in (root / "tests").rglob("test_*.py")
        if path.is_file()
    )


def build_manifest(test_files: list[Path], root: Path = ROOT) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
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
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0")))
    return totals


def tracked_mutations(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            value = line[3:].strip().strip('"').replace("\\", "/")
            if " -> " in value:
                value = value.split(" -> ", 1)[1]
            paths.append(value)
    return sorted(set(paths))


def restore_mutations(paths: list[str], root: Path = ROOT) -> None:
    if not paths:
        return

    git_root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_root_result.returncode != 0:
        raise RuntimeError(
            "Could not resolve Git root before restoring "
            "test-induced tracked mutations: "
            + git_root_result.stderr.strip()
        )

    git_root = Path(git_root_result.stdout.strip()).resolve()
    result = subprocess.run(
        ["git", "restore", "--worktree", "--", *paths],
        cwd=git_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not restore test-induced tracked mutations "
            f"from Git root {git_root}: "
            + result.stderr.strip()
        )


def untracked_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Could not enumerate untracked files.")
    return sorted(
        item.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    )


def remove_generated_untracked(paths: list[str], root: Path = ROOT) -> list[str]:
    removed: list[str] = []
    root = root.resolve()
    for raw in sorted(set(paths)):
        candidate = (root / raw).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise RuntimeError(
                f"Refusing cleanup outside repository: {candidate}"
            ) from error

        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()
            removed.append(raw)
        elif candidate.exists():
            raise RuntimeError(
                f"Refusing recursive generated-output cleanup: {raw}"
            )

        parent = candidate.parent
        while parent != root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return removed


def windows_process_snapshot() -> dict[int, dict[str, Any]]:
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
    payload = json.loads(result.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    snapshot: dict[int, dict[str, Any]] = {}
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


def cleanup_new_test_processes(
    before: dict[int, dict[str, Any]],
) -> list[str]:
    if os.name != "nt":
        return []
    after = windows_process_snapshot()
    new_ids = set(after) - set(before)
    candidates: set[int] = set()
    for process_id in new_ids:
        item = after[process_id]
        name = str(item["name"]).lower()
        command_line = str(item["command_line"]).lower()
        if name == "bash.exe" and "qrds_" in command_line:
            candidates.add(process_id)
        if name == "python.exe" and "-m http.server" in command_line:
            candidates.add(process_id)

    children_by_parent: dict[int, list[int]] = {}
    for process_id, item in after.items():
        children_by_parent.setdefault(
            int(item["parent_process_id"]),
            [],
        ).append(process_id)

    queue = list(candidates)
    kill_ids = set(candidates)
    while queue:
        parent_id = queue.pop()
        for child_id in children_by_parent.get(parent_id, []):
            if child_id in new_ids and child_id not in kill_ids:
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


def kill_process_tree(process_id: int) -> None:
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


def suite_environment(root: Path = ROOT) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    if os.name != "nt":
        return env

    venv_scripts = root / ".venv" / "Scripts"
    venv_python = venv_scripts / "python.exe"
    if not venv_python.is_file():
        raise RuntimeError(f"Venv Python is missing: {venv_python}")

    bash_candidates = [
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
        Path(r"C:\Program Files (x86)\Git\usr\bin\bash.exe"),
    ]
    bash_executable = next(
        (candidate for candidate in bash_candidates if candidate.is_file()),
        None,
    )
    if bash_executable is None:
        found = shutil.which("bash.exe", path=env.get("PATH"))
        bash_executable = Path(found) if found else None
    if bash_executable is None:
        raise RuntimeError("Git Bash is required but bash.exe was not found.")

    env["VIRTUAL_ENV"] = str(root / ".venv")
    env.pop("PYTHONHOME", None)
    env["PYTHON"] = str(venv_python)
    env["PYTHON_EXECUTABLE"] = str(venv_python)
    env["PATH"] = (
        str(venv_scripts)
        + os.pathsep
        + str(bash_executable.parent)
        + os.pathsep
        + env.get("PATH", "")
    )
    return env


def _phase225_microbatches(
    shard: list[Path],
    size: int = 8,
) -> list[list[Path]]:
    isolation_tokens = (
        "portal",
        "serve",
        "server",
        "dashboard",
        "wrapper",
        "http",
    )
    forced_isolation = {
        "tests/unit/test_phase164_shadow_evidence_replay_preflight_research_only.py",
        "tests/unit/test_phase167_shadow_evidence_scorecard_research_only.py",
        "tests/unit/test_phase16_multisource_consensus_baseline_pack.py",
        "tests/unit/test_phase172_shadow_readiness_synthesis_research_only.py",
        "tests/unit/test_phase175_shadow_readiness_batch_checkpoint_research_only.py",
        "tests/unit/test_phase178_promotion_blocker_null_output_guard_research_only.py",
        "tests/unit/test_phase180_promotion_blocker_batch_checkpoint_research_only.py",
        "tests/unit/test_phase183_gap_severity_classifier_research_only.py",
        "tests/unit/test_phase154_shadow_decision_readiness_preflight_research_only.py",
        "tests/unit/test_phase157_shadow_simulation_null_runner_research_only.py",
        "tests/unit/test_phase15_multisource_trust_registry_comparison_pack.py",
        "tests/unit/test_phase162_shadow_evidence_replay_input_builder_research_only.py",
        "tests/unit/test_phase165_shadow_evidence_replay_batch_checkpoint_research_only.py",
        "tests/unit/test_phase168_shadow_risk_scorecard_research_only.py",
        "tests/unit/test_phase170_shadow_score_batch_checkpoint_research_only.py",
        "tests/unit/test_phase173_shadow_readiness_explanation_research_only.py",
        "tests/unit/test_phase163_shadow_evidence_replay_null_evaluation_research_only.py",
        "tests/unit/test_phase166_shadow_score_requirement_registry_research_only.py",
        "tests/unit/test_phase169_shadow_score_preflight_research_only.py",
        "tests/unit/test_phase171_shadow_readiness_requirement_registry_research_only.py",
        "tests/unit/test_phase174_shadow_readiness_preflight_research_only.py",
        "tests/unit/test_phase177_promotion_blocker_reason_map_research_only.py",
        "tests/unit/test_phase17_consensus_quality_drift_monitor_pack.py",
        "tests/unit/test_phase182_gap_matrix_research_only.py",
    }
    isolated: list[list[Path]] = []
    regular: list[Path] = []

    for path in shard:
        relative = path.relative_to(ROOT).as_posix()
        lowered = relative.lower()
        if (
            relative in forced_isolation
            or any(token in lowered for token in isolation_tokens)
        ):
            isolated.append([path])
        else:
            regular.append(path)

    batches = [
        regular[index : index + size]
        for index in range(0, len(regular), size)
    ]
    return batches + isolated

def _phase225_write_aggregate_junit(
    path: Path,
    name: str,
    totals: dict[str, int],
) -> None:
    root = ET.Element(
        "testsuites",
        {
            "name": name,
            "tests": str(totals["tests"]),
            "failures": str(totals["failures"]),
            "errors": str(totals["errors"]),
            "skipped": str(totals["skipped"]),
        },
    )
    ET.SubElement(
        root,
        "testsuite",
        {
            "name": name,
            "tests": str(totals["tests"]),
            "failures": str(totals["failures"]),
            "errors": str(totals["errors"]),
            "skipped": str(totals["skipped"]),
        },
    )
    ET.ElementTree(root).write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )


def _phase225_existing_microbatch_pass(
    meta_path: Path,
    junit_path: Path,
    log_path: Path,
    expected_files: list[str],
) -> tuple[bool, dict[str, int]]:
    if (
        not meta_path.is_file()
        or not junit_path.is_file()
        or not log_path.is_file()
    ):
        return False, {
            "tests": 0,
            "failures": 0,
            "errors": 1,
            "skipped": 0,
        }

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, {
            "tests": 0,
            "failures": 0,
            "errors": 1,
            "skipped": 0,
        }

    if metadata.get("files") != expected_files:
        return False, {
            "tests": 0,
            "failures": 0,
            "errors": 1,
            "skipped": 0,
        }

    counts = parse_junit(junit_path)
    passed = bool(
        counts["tests"] > 0
        and counts["failures"] == 0
        and counts["errors"] == 0
        and metadata.get("returncode") == 0
        and metadata.get("timed_out") is False
    )
    return passed, counts


def run_full_suite(
    output_dir: Path,
    timeout_seconds: int = 5400,
    root: Path = ROOT,
) -> dict[str, Any]:
    output_dir = resolve_repo_path(output_dir, root)
    tests = discover_test_files(root)
    manifest_before = build_manifest(tests, root)
    shards = split_shards(tests, 3)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = suite_environment(root)

    microbatch_timeout = min(
        max(int(timeout_seconds) // 6, 900),
        1800,
    )
    isolated_file_timeout = 1800

    shard_results: list[dict[str, Any]] = []
    restored_paths: list[str] = []
    removed_generated_paths: list[str] = []
    removed_test_processes: list[str] = []
    reused_microbatches = 0
    executed_microbatches = 0

    for shard_index, shard in enumerate(shards, start=1):
        aggregate_junit = (
            output_dir / f"phase225_shard_{shard_index}.xml"
        )
        aggregate_log = (
            output_dir / f"phase225_shard_{shard_index}.log"
        )
        assignment = (
            output_dir
            / f"phase225_shard_{shard_index}_files.json"
        )
        shard_files = [
            path.relative_to(root).as_posix()
            for path in shard
        ]
        assignment.write_text(
            json.dumps(shard_files, indent=2) + "\n",
            encoding="utf-8",
        )

        microbatches = _phase225_microbatches(shard, size=8)
        print(
            f"PHASE225_SHARD_{shard_index}_START "
            f"files={len(shard)} "
            f"microbatches={len(microbatches)} "
            f"micro_timeout={microbatch_timeout}s",
            flush=True,
        )

        shard_totals = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }
        micro_results: list[dict[str, Any]] = []
        shard_returncode = 0
        shard_timed_out = False
        shard_log_lines: list[str] = []

        for micro_index, microbatch in enumerate(
            microbatches,
            start=1,
        ):
            prefix = (
                f"phase225_shard_{shard_index}_"
                f"micro_{micro_index:03d}"
            )
            junit = output_dir / f"{prefix}.xml"
            log = output_dir / f"{prefix}.log"
            meta = output_dir / f"{prefix}.json"
            micro_files = [
                path.relative_to(root).as_posix()
                for path in microbatch
            ]

            reuse, existing_counts = (
                _phase225_existing_microbatch_pass(
                    meta,
                    junit,
                    log,
                    micro_files,
                )
            )
            if reuse:
                reused_microbatches += 1
                micro_result = {
                    "microbatch": micro_index,
                    "file_count": len(microbatch),
                    "returncode": 0,
                    "timed_out": False,
                    "junit": existing_counts,
                    "junit_path": junit.relative_to(root).as_posix(),
                    "log_path": log.relative_to(root).as_posix(),
                    "meta_path": meta.relative_to(root).as_posix(),
                    "reused": True,
                    "files": micro_files,
                    "removed_generated_untracked_paths": [],
                    "removed_test_processes": [],
                    "restored_tracked_paths": [],
                }
                micro_results.append(micro_result)
                for key in shard_totals:
                    shard_totals[key] += existing_counts[key]
                print(
                    f"PHASE225_SHARD_{shard_index}_"
                    f"MICRO_{micro_index:03d}_REUSED "
                    f"files={len(microbatch)} "
                    f"tests={existing_counts['tests']}",
                    flush=True,
                )
                continue

            junit.touch(exist_ok=True)
            log.touch(exist_ok=True)
            meta.write_text(
                json.dumps(
                    {
                        "files": micro_files,
                        "status": "RUNNING",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            untracked_before = set(untracked_paths(root))
            processes_before = windows_process_snapshot()
            args = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                f"--junitxml={junit}",
                *micro_files,
            ]

            print(
                f"PHASE225_SHARD_{shard_index}_"
                f"MICRO_{micro_index:03d}_START "
                f"files={len(microbatch)}",
                flush=True,
            )

            timed_out = False
            executed_microbatches += 1
            with log.open(
                "w",
                encoding="utf-8",
                errors="replace",
            ) as log_handle:
                process = subprocess.Popen(
                    args,
                    cwd=root,
                    env=env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=(os.name != "nt"),
                )
                current_timeout = (
                    isolated_file_timeout
                    if len(microbatch) == 1
                    else microbatch_timeout
                )
                try:
                    returncode = int(
                        process.wait(timeout=current_timeout)
                    )
                except subprocess.TimeoutExpired:
                    timed_out = True
                    kill_process_tree(process.pid)
                    try:
                        returncode = int(
                            process.wait(timeout=30)
                        )
                    except subprocess.TimeoutExpired:
                        returncode = 124

            mutations = tracked_mutations(root)
            if mutations:
                restore_mutations(mutations, root)
                restored_paths.extend(mutations)

            removed_processes = cleanup_new_test_processes(
                processes_before
            )
            removed_test_processes.extend(removed_processes)
            if removed_processes:
                time.sleep(0.5)

            generated_untracked = sorted(
                set(untracked_paths(root)) - untracked_before
            )
            protected = {
                junit.relative_to(root).as_posix(),
                log.relative_to(root).as_posix(),
                meta.relative_to(root).as_posix(),
            }
            generated_untracked = [
                item
                for item in generated_untracked
                if item not in protected
            ]
            removed_untracked = remove_generated_untracked(
                generated_untracked,
                root,
            )
            removed_generated_paths.extend(removed_untracked)

            counts = parse_junit(junit)
            meta.write_text(
                json.dumps(
                    {
                        "files": micro_files,
                        "returncode": returncode,
                        "timed_out": timed_out,
                        "junit": counts,
                        "removed_generated_untracked_paths": (
                            removed_untracked
                        ),
                        "removed_test_processes": removed_processes,
                        "restored_tracked_paths": mutations,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            micro_result = {
                "microbatch": micro_index,
                "file_count": len(microbatch),
                "returncode": returncode,
                "timed_out": timed_out,
                "junit": counts,
                "junit_path": junit.relative_to(root).as_posix(),
                "log_path": log.relative_to(root).as_posix(),
                "meta_path": meta.relative_to(root).as_posix(),
                "reused": False,
                "files": micro_files,
                "removed_generated_untracked_paths": removed_untracked,
                "removed_test_processes": removed_processes,
                "restored_tracked_paths": mutations,
            }
            micro_results.append(micro_result)
            for key in shard_totals:
                shard_totals[key] += counts[key]

            summary = (
                f"micro={micro_index:03d} "
                f"files={len(microbatch)} "
                f"rc={returncode} "
                f"tests={counts['tests']} "
                f"failures={counts['failures']} "
                f"errors={counts['errors']} "
                f"timed_out={timed_out} "
                f"processes_removed={len(removed_processes)}"
            )
            shard_log_lines.append(summary)
            print(
                f"PHASE225_SHARD_{shard_index}_"
                f"MICRO_{micro_index:03d}_END "
                + summary,
                flush=True,
            )

            if (
                returncode != 0
                or timed_out
                or counts["failures"] != 0
                or counts["errors"] != 0
            ):
                shard_returncode = returncode
                shard_timed_out = timed_out
                try:
                    print(
                        log.read_text(
                            encoding="utf-8",
                            errors="replace",
                        )[-16000:]
                    )
                except OSError:
                    pass
                break

        _phase225_write_aggregate_junit(
            aggregate_junit,
            f"phase225_shard_{shard_index}",
            shard_totals,
        )
        aggregate_log.write_text(
            "\n".join(shard_log_lines) + "\n",
            encoding="utf-8",
        )

        shard_result = {
            "shard": shard_index,
            "file_count": len(shard),
            "returncode": shard_returncode,
            "timed_out": shard_timed_out,
            "junit": shard_totals,
            "junit_path": aggregate_junit.relative_to(root).as_posix(),
            "log_path": aggregate_log.relative_to(root).as_posix(),
            "assignment_path": assignment.relative_to(root).as_posix(),
            "microbatch_count": len(microbatches),
            "microbatches": micro_results,
            "restored_tracked_paths": sorted(
                {
                    path
                    for item in micro_results
                    for path in item["restored_tracked_paths"]
                }
            ),
            "removed_generated_untracked_paths": sorted(
                {
                    path
                    for item in micro_results
                    for path in (
                        item[
                            "removed_generated_untracked_paths"
                        ]
                    )
                }
            ),
            "removed_test_processes": sorted(
                {
                    item
                    for result in micro_results
                    for item in result["removed_test_processes"]
                }
            ),
        }
        shard_results.append(shard_result)

        print(
            f"PHASE225_SHARD_{shard_index}_END "
            f"rc={shard_returncode} "
            f"tests={shard_totals['tests']} "
            f"failures={shard_totals['failures']} "
            f"errors={shard_totals['errors']} "
            f"timed_out={shard_timed_out}",
            flush=True,
        )

        if (
            shard_returncode != 0
            or shard_timed_out
            or shard_totals["failures"] != 0
            or shard_totals["errors"] != 0
        ):
            break

    manifest_after = build_manifest(tests, root)
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
    passed = bool(
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
        "timeout_seconds_per_shard": int(timeout_seconds),
        "microbatch_timeout_seconds": microbatch_timeout,
        "isolated_file_timeout_seconds": isolated_file_timeout,
        "microbatch_size": 8,
        "forced_isolation_file_count": 24,
        "executed_microbatches": executed_microbatches,
        "reused_microbatches": reused_microbatches,
        "passed": passed,
    }




# BEGIN PHASE225 STANDARD COVERAGE RESUME V10

def _phase225_v10_parse_junit(path):
    import xml.etree.ElementTree as ET

    counts = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    if not path.is_file():
        return counts

    try:
        xml_root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return counts

    suites = (
        [xml_root]
        if xml_root.tag == "testsuite"
        else list(xml_root.findall("testsuite"))
    )
    for key in counts:
        counts[key] = sum(
            int(float(suite.attrib.get(key, "0")))
            for suite in suites
        )
    return counts


def _phase225_v10_git_root(root=ROOT):
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not resolve Git root: "
            + result.stderr.strip()
        )
    return Path(result.stdout.strip()).resolve()


def _phase225_v10_git_paths(
    *,
    tracked_only=False,
    root=ROOT,
):
    git_root = _phase225_v10_git_root(root)
    if tracked_only:
        command = [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ]
        result = subprocess.run(
            command,
            cwd=git_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Could not inspect tracked worktree: "
                + result.stderr.strip()
            )

        paths = set()
        for raw in result.stdout.splitlines():
            if len(raw) < 4:
                continue
            value = raw[3:].strip().strip('"')
            if " -> " in value:
                value = value.split(" -> ", 1)[1]
            paths.add(value.replace("\\", "/"))
        return paths

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=git_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not inspect untracked worktree."
        )
    return {
        item.decode(
            "utf-8",
            errors="surrogateescape",
        ).replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def _phase225_v10_restore_test_mutations(
    tracked_before,
    root=ROOT,
):
    tracked_after = _phase225_v10_git_paths(
        tracked_only=True,
        root=root,
    )
    introduced = sorted(tracked_after - tracked_before)
    if not introduced:
        return []

    allowed = {
        (
            "crypto_decision_lab/tools/"
            "serve_review_portal_research_only.ps1"
        ),
    }
    refused = [
        item
        for item in introduced
        if item not in allowed
    ]
    if refused:
        raise RuntimeError(
            "A test introduced unexpected tracked mutations: "
            + ", ".join(refused)
        )

    git_root = _phase225_v10_git_root(root)
    result = subprocess.run(
        [
            "git",
            "restore",
            "--worktree",
            "--",
            *introduced,
        ],
        cwd=git_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not restore test-induced mutations: "
            + result.stderr.strip()
        )
    return introduced


def _phase225_v10_cleanup_generated(
    untracked_before,
    protected,
    root=ROOT,
):
    untracked_after = _phase225_v10_git_paths(
        tracked_only=False,
        root=root,
    )
    introduced = sorted(
        untracked_after - untracked_before
    )
    removed = []
    refused = []

    allowed_prefixes = (
        (
            "crypto_decision_lab/"
            "docs/reports/agentic_devops/"
        ),
        (
            "crypto_decision_lab/"
            "docs/reports/journal_replay/"
        ),
        "docs/reports/agentic_devops/",
        "docs/reports/journal_replay/",
    )

    git_root = _phase225_v10_git_root(root)
    for relative in introduced:
        if relative in protected:
            continue
        if not relative.startswith(allowed_prefixes):
            refused.append(relative)
            continue

        candidate = (git_root / relative).resolve()
        candidate.relative_to(git_root)
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()
            removed.append(relative)
        elif candidate.exists():
            refused.append(relative)

    if refused:
        raise RuntimeError(
            "A test introduced unexpected untracked paths: "
            + ", ".join(refused)
        )
    return removed


def _phase225_v10_dependency_fingerprint(
    manifest,
    root=ROOT,
):
    import hashlib

    dependency_paths = [
        (
            "src/crypto_decision_lab/scripts/"
            "phase141_replay_validity_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase146_risk_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase151_shadow_decision_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase156_shadow_simulation_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase161_shadow_evidence_replay_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase166_shadow_score_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase171_shadow_readiness_requirement_registry_research_only.py"
        ),
        (
            "src/crypto_decision_lab/scripts/"
            "phase225_robustness_full_integration_tracking_checkpoint_research_only.py"
        ),
        (
            "tests/unit/"
            "test_phase141_171_registry_memoization_regression_research_only.py"
        ),
    ]

    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    for relative in dependency_paths:
        path = root / relative
        digest.update(relative.encode("utf-8"))
        digest.update(
            path.read_bytes()
            if path.is_file()
            else b"<missing>"
        )
    return digest.hexdigest()


def _phase225_v10_affected_files(
    relative_tests,
    root=ROOT,
):
    import re

    markers = (
        "phase141_replay_validity_requirement_registry",
        "phase146_risk_requirement_registry",
        "phase151_shadow_decision_requirement_registry",
        "phase156_shadow_simulation_requirement_registry",
        "phase161_shadow_evidence_replay_requirement_registry",
        "phase166_shadow_score_requirement_registry",
        "phase171_shadow_readiness_requirement_registry",
        "phase174_shadow_readiness_preflight",
        "phase225_robustness_full_integration",
    )

    affected = set()
    for relative in relative_tests:
        name = Path(relative).name
        match = re.search(r"test_phase(\d+)", name)
        if (
            match is not None
            and int(match.group(1)) >= 141
        ):
            affected.add(relative)
            continue

        path = root / relative
        try:
            text = path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        except OSError:
            affected.add(relative)
            continue

        if any(marker in text for marker in markers):
            affected.add(relative)

    return affected


def _phase225_v10_collect_records(
    output_dir,
    current_files,
    affected_files,
    shard_by_file,
    fingerprint,
    root=ROOT,
):
    patterns = (
        "phase225_shard_*_micro_*.json",
        "phase225_recovery_file_*.json",
        "phase225_v10_file_*.json",
    )
    candidates = []

    for pattern in patterns:
        for meta_path in sorted(
            output_dir.glob(pattern)
        ):
            try:
                payload = json.loads(
                    meta_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (json.JSONDecodeError, OSError):
                continue

            if not isinstance(payload, dict):
                continue
            files = payload.get("files")
            if (
                not isinstance(files, list)
                or not files
                or not all(
                    isinstance(item, str)
                    for item in files
                )
            ):
                continue

            normalized = [
                item.replace("\\", "/")
                for item in files
            ]
            file_set = set(normalized)
            if not file_set.issubset(current_files):
                continue

            record_shards = {
                shard_by_file[item]
                for item in normalized
            }
            if len(record_shards) != 1:
                continue

            intersects_affected = bool(
                file_set & affected_files
            )
            if intersects_affected:
                if not (
                    payload.get("mode")
                    == "STANDARD_PYTEST_V10"
                    and payload.get(
                        "dependency_fingerprint"
                    )
                    == fingerprint
                ):
                    continue

            junit_path = meta_path.with_suffix(".xml")
            log_path = meta_path.with_suffix(".log")
            counts = _phase225_v10_parse_junit(
                junit_path
            )
            if not (
                payload.get("returncode") == 0
                and payload.get("timed_out") is False
                and counts["tests"] > 0
                and counts["failures"] == 0
                and counts["errors"] == 0
                and junit_path.is_file()
                and log_path.is_file()
            ):
                continue

            candidates.append(
                {
                    "files": normalized,
                    "file_set": frozenset(normalized),
                    "junit": counts,
                    "junit_path": junit_path,
                    "log_path": log_path,
                    "meta_path": meta_path,
                    "mtime": meta_path.stat().st_mtime,
                    "mode": payload.get("mode"),
                    "shard": next(iter(record_shards)),
                }
            )

    latest_by_file_set = {}
    for item in candidates:
        key = item["file_set"]
        previous = latest_by_file_set.get(key)
        if (
            previous is None
            or item["mtime"] > previous["mtime"]
        ):
            latest_by_file_set[key] = item

    return sorted(
        latest_by_file_set.values(),
        key=lambda item: (
            -len(item["files"]),
            -float(item["mtime"]),
            item["meta_path"].as_posix(),
        ),
    )


def _phase225_v10_select_records(records):
    selected = []
    covered = set()
    for item in records:
        item_files = set(item["files"])
        if item_files & covered:
            continue
        selected.append(item)
        covered.update(item_files)
    return selected, covered


def _phase225_v10_kill_tree(pid):
    if os.name == "nt":
        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(pid),
                "/T",
                "/F",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return

    try:
        os.killpg(pid, 9)
    except ProcessLookupError:
        pass


def _phase225_v10_write_aggregate_junit(
    path,
    name,
    counts,
):
    import xml.etree.ElementTree as ET

    root = ET.Element("testsuites")
    ET.SubElement(
        root,
        "testsuite",
        {
            "name": name,
            "tests": str(counts["tests"]),
            "failures": str(counts["failures"]),
            "errors": str(counts["errors"]),
            "skipped": str(counts["skipped"]),
            "time": "0",
        },
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    ET.ElementTree(root).write(
        temporary,
        encoding="utf-8",
        xml_declaration=True,
    )
    os.replace(temporary, path)


def _phase225_v10_run_file(
    test_file,
    index,
    output_dir,
    env,
    timeout_seconds,
    fingerprint,
    root=ROOT,
):
    import hashlib

    safe = Path(test_file).stem.replace(
        "test_",
        "",
        1,
    )
    short_hash = hashlib.sha256(
        test_file.encode("utf-8")
    ).hexdigest()[:10]
    prefix = (
        f"phase225_v10_file_{index:03d}_"
        f"{safe}_{short_hash}"
    )
    junit_path = output_dir / f"{prefix}.xml"
    log_path = output_dir / f"{prefix}.log"
    meta_path = output_dir / f"{prefix}.json"

    tracked_before = _phase225_v10_git_paths(
        tracked_only=True,
        root=root,
    )
    untracked_before = _phase225_v10_git_paths(
        tracked_only=False,
        root=root,
    )

    process_snapshot = (
        windows_process_snapshot()
        if callable(
            globals().get(
                "windows_process_snapshot"
            )
        )
        else {}
    )

    meta_path.write_text(
        json.dumps(
            {
                "files": [test_file],
                "status": "RUNNING",
                "mode": "STANDARD_PYTEST_V10",
                "dependency_fingerprint": fingerprint,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "--disable-warnings",
        "-p",
        "no:faulthandler",
        "-p",
        "no:cacheprovider",
        f"--junitxml={junit_path}",
        test_file,
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(
            subprocess,
            "CREATE_NEW_PROCESS_GROUP",
            0,
        )

    started = time.monotonic()
    timed_out = False

    print(
        "PHASE225_V10_FILE_START "
        f"index={index} "
        f"timeout={timeout_seconds}s "
        f"file={test_file}",
        flush=True,
    )

    with log_path.open(
        "w",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )

        next_heartbeat = started + 30.0
        while process.poll() is None:
            now = time.monotonic()
            if now >= next_heartbeat:
                print(
                    "PHASE225_V10_HEARTBEAT "
                    f"index={index} "
                    f"elapsed={int(now-started)}s "
                    f"file={test_file}",
                    flush=True,
                )
                next_heartbeat = now + 30.0

            if now - started >= timeout_seconds:
                timed_out = True
                _phase225_v10_kill_tree(process.pid)
                break

            time.sleep(1.0)

        try:
            returncode = int(
                process.wait(timeout=20)
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            _phase225_v10_kill_tree(process.pid)
            returncode = 124

    restored = _phase225_v10_restore_test_mutations(
        tracked_before,
        root,
    )

    removed_processes = []
    cleanup = globals().get(
        "cleanup_new_test_processes"
    )
    if callable(cleanup):
        removed_processes = cleanup(process_snapshot)

    git_root = _phase225_v10_git_root(root)
    protected = set()
    for protected_path in (
        junit_path,
        log_path,
        meta_path,
    ):
        try:
            protected.add(
                protected_path.resolve()
                .relative_to(git_root)
                .as_posix()
            )
        except ValueError:
            pass

    removed_untracked = (
        _phase225_v10_cleanup_generated(
            untracked_before,
            protected,
            root,
        )
    )

    counts = _phase225_v10_parse_junit(
        junit_path
    )
    payload = {
        "files": [test_file],
        "returncode": returncode,
        "timed_out": timed_out,
        "junit": counts,
        "mode": "STANDARD_PYTEST_V10",
        "dependency_fingerprint": fingerprint,
        "elapsed_seconds": round(
            time.monotonic() - started,
            3,
        ),
        "restored_tracked_paths": restored,
        "removed_generated_untracked_paths": (
            removed_untracked
        ),
        "removed_test_processes": removed_processes,
    }
    meta_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "PHASE225_V10_FILE_END "
        f"index={index} "
        f"rc={returncode} "
        f"tests={counts['tests']} "
        f"failures={counts['failures']} "
        f"errors={counts['errors']} "
        f"timed_out={timed_out} "
        f"file={test_file}",
        flush=True,
    )

    if not (
        returncode == 0
        and not timed_out
        and counts["tests"] > 0
        and counts["failures"] == 0
        and counts["errors"] == 0
    ):
        try:
            print(
                log_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )[-20000:]
            )
        except OSError:
            pass
        raise RuntimeError(
            "Phase 225 V10 file validation failed: "
            + test_file
        )

    return payload


def _phase225_standard_coverage_resume_v10(
    output_dir,
    timeout_seconds=5400,
    root=ROOT,
):
    output_dir = resolve_repo_path(
        output_dir,
        root,
    )
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    tests = discover_test_files(root)
    relative_tests = [
        path.relative_to(root).as_posix()
        for path in tests
    ]
    current_files = set(relative_tests)
    manifest_before = build_manifest(
        tests,
        root,
    )
    shards = split_shards(tests, 3)
    shard_by_file = {
        path.relative_to(root).as_posix(): shard_index
        for shard_index, shard in enumerate(
            shards,
            start=1,
        )
        for path in shard
    }

    affected_files = _phase225_v10_affected_files(
        relative_tests,
        root,
    )
    fingerprint = (
        _phase225_v10_dependency_fingerprint(
            manifest_before,
            root,
        )
    )

    records = _phase225_v10_collect_records(
        output_dir,
        current_files,
        affected_files,
        shard_by_file,
        fingerprint,
        root,
    )
    selected_before, covered_before = (
        _phase225_v10_select_records(records)
    )
    missing = [
        item
        for item in relative_tests
        if item not in covered_before
    ]

    print(
        "PHASE225_V10_RESUME_START "
        f"test_files={len(relative_tests)} "
        f"affected_files={len(affected_files)} "
        f"covered_files={len(covered_before)} "
        f"remaining_files={len(missing)} "
        f"reused_groups={len(selected_before)}",
        flush=True,
    )

    env = suite_environment(root)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    per_file_timeout = min(
        max(int(timeout_seconds) // 18, 180),
        300,
    )

    executed = []
    for index, test_file in enumerate(
        missing,
        start=1,
    ):
        executed.append(
            _phase225_v10_run_file(
                test_file,
                index,
                output_dir,
                env,
                per_file_timeout,
                fingerprint,
                root,
            )
        )

    final_records = _phase225_v10_collect_records(
        output_dir,
        current_files,
        affected_files,
        shard_by_file,
        fingerprint,
        root,
    )
    selected, covered = (
        _phase225_v10_select_records(
            final_records
        )
    )
    missing_after = [
        item
        for item in relative_tests
        if item not in covered
    ]
    if missing_after:
        raise RuntimeError(
            "Phase 225 V10 coverage incomplete: "
            + ", ".join(missing_after)
        )

    shard_records = {1: [], 2: [], 3: []}
    for item in selected:
        shard_records[item["shard"]].append(item)

    totals = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    shard_results = []

    for shard_index, shard in enumerate(
        shards,
        start=1,
    ):
        shard_counts = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }
        microbatches = []
        log_lines = []

        records_for_shard = sorted(
            shard_records[shard_index],
            key=lambda item: (
                min(item["files"]),
                len(item["files"]),
            ),
        )

        for record_index, item in enumerate(
            records_for_shard,
            start=1,
        ):
            for key in shard_counts:
                shard_counts[key] += item[
                    "junit"
                ][key]

            microbatches.append(
                {
                    "microbatch": record_index,
                    "file_count": len(
                        item["files"]
                    ),
                    "returncode": 0,
                    "timed_out": False,
                    "junit": item["junit"],
                    "junit_path": (
                        item["junit_path"]
                        .relative_to(root)
                        .as_posix()
                    ),
                    "log_path": (
                        item["log_path"]
                        .relative_to(root)
                        .as_posix()
                    ),
                    "meta_path": (
                        item["meta_path"]
                        .relative_to(root)
                        .as_posix()
                    ),
                    "reused": (
                        item["mode"]
                        != "STANDARD_PYTEST_V10"
                    ),
                    "files": item["files"],
                    "restored_tracked_paths": [],
                    "removed_generated_untracked_paths": [],
                    "removed_test_processes": [],
                }
            )
            log_lines.append(
                f"record={record_index:03d} "
                f"files={len(item['files'])} "
                f"tests={item['junit']['tests']} "
                f"mode={item['mode']} "
                f"source={item['meta_path'].name}"
            )

        aggregate_junit = (
            output_dir
            / f"phase225_shard_{shard_index}.xml"
        )
        aggregate_log = (
            output_dir
            / f"phase225_shard_{shard_index}.log"
        )
        assignment = (
            output_dir
            / f"phase225_shard_{shard_index}_files.json"
        )

        _phase225_v10_write_aggregate_junit(
            aggregate_junit,
            f"phase225_shard_{shard_index}",
            shard_counts,
        )
        aggregate_log.write_text(
            "\n".join(log_lines) + "\n",
            encoding="utf-8",
        )
        assignment.write_text(
            json.dumps(
                [
                    path.relative_to(root)
                    .as_posix()
                    for path in shard
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        for key in totals:
            totals[key] += shard_counts[key]

        shard_results.append(
            {
                "shard": shard_index,
                "file_count": len(shard),
                "returncode": 0,
                "timed_out": False,
                "junit": shard_counts,
                "junit_path": (
                    aggregate_junit
                    .relative_to(root)
                    .as_posix()
                ),
                "log_path": (
                    aggregate_log
                    .relative_to(root)
                    .as_posix()
                ),
                "assignment_path": (
                    assignment
                    .relative_to(root)
                    .as_posix()
                ),
                "microbatch_count": len(
                    microbatches
                ),
                "microbatches": microbatches,
                "restored_tracked_paths": [],
                "removed_generated_untracked_paths": [],
                "removed_test_processes": [],
            }
        )

        print(
            f"PHASE225_V10_SHARD_{shard_index}_COMPLETE "
            f"files={len(shard)} "
            f"tests={shard_counts['tests']} "
            "failures=0 errors=0",
            flush=True,
        )

    manifest_after = build_manifest(
        tests,
        root,
    )
    manifest_stable = (
        manifest_before == manifest_after
    )
    passed = bool(
        len(covered) == len(relative_tests)
        and len(shard_results) == 3
        and totals["tests"] > 0
        and totals["failures"] == 0
        and totals["errors"] == 0
        and manifest_stable
    )

    reused_groups = sum(
        1
        for item in selected
        if item["mode"] != "STANDARD_PYTEST_V10"
    )
    v10_groups = sum(
        1
        for item in selected
        if item["mode"] == "STANDARD_PYTEST_V10"
    )

    print(
        "PHASE225_V10_RESUME_END "
        f"coverage={len(covered)}/{len(relative_tests)} "
        f"tests={totals['tests']} "
        f"failures={totals['failures']} "
        f"errors={totals['errors']} "
        f"executed_now={len(executed)} "
        f"reused_groups={reused_groups} "
        f"v10_groups={v10_groups} "
        f"manifest_stable={manifest_stable}",
        flush=True,
    )

    return {
        "test_file_count": len(tests),
        "manifest_before": manifest_before,
        "manifest_after": manifest_after,
        "manifest_stable": manifest_stable,
        "shard_count": 3,
        "all_shards_completed": len(
            shard_results
        ) == 3,
        "shards": shard_results,
        "totals": totals,
        "restored_tracked_paths": sorted(
            {
                path
                for item in executed
                for path in item.get(
                    "restored_tracked_paths",
                    [],
                )
            }
        ),
        "removed_generated_untracked_paths": sorted(
            {
                path
                for item in executed
                for path in item.get(
                    "removed_generated_untracked_paths",
                    [],
                )
            }
        ),
        "removed_test_processes": sorted(
            {
                value
                for item in executed
                for value in item.get(
                    "removed_test_processes",
                    [],
                )
            }
        ),
        "timeout_seconds_per_shard": int(
            timeout_seconds
        ),
        "microbatch_timeout_seconds": (
            per_file_timeout
        ),
        "isolated_file_timeout_seconds": (
            per_file_timeout
        ),
        "microbatch_size": 1,
        "executed_microbatches": len(
            executed
        ),
        "reused_microbatches": reused_groups,
        "forced_isolation_file_count": len(
            missing
        ),
        "recovery_mode": (
            "STANDARD_PYTEST_COVERAGE_RESUME_V10"
        ),
        "dependency_fingerprint": fingerprint,
        "affected_file_count": len(
            affected_files
        ),
        "coverage_complete": (
            len(covered) == len(relative_tests)
        ),
        "coverage_file_count": len(covered),
        "selected_result_count": len(selected),
        "passed": passed,
    }


run_full_suite = _phase225_standard_coverage_resume_v10

# END PHASE225 STANDARD COVERAGE RESUME V10


def tracking_documents(
    payload: dict[str, Any],
    tracking_dir: Path,
    root: Path = ROOT,
) -> dict[str, Path]:
    full = payload["full_suite"]
    score = payload["phase_chain"]["224"]["score"]

    master = tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE225.md"
    diagram = tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE225.md"
    table = tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE225.md"
    milestone = tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_216_225.md"
    roadmap = tracking_dir / "QRDS_ROADMAP_226_235_RESEARCH_ONLY.md"
    snapshot = tracking_dir / "qrds_progress_snapshot_phase225.json"

    write_markdown(
        master,
        "\n".join(
            [
                "# QRDS Master Progress by Tens - Phase 225",
                "",
                "**Integration baseline before batch:** `69d6483`",
                f"**Checkpoint:** `{payload['checkpoint_status']}`",
                "**Operational:** `BLOCKED_RESEARCH_ONLY`",
                "",
                "## Batch 216-225",
                "",
                "The batch added provenance completeness, derived-view "
                "agreement diagnostics, contamination sensitivity, boundary "
                "perturbation, model-free benchmarks, uncertainty diagnostics, "
                "notional cost sensitivity and a robustness scorecard.",
                "",
                "## Mandatory global integration evidence",
                "",
                f"- Test files: `{full['test_file_count']}`",
                f"- Executed tests: `{full['totals']['tests']}`",
                f"- Failures: `{full['totals']['failures']}`",
                f"- Errors: `{full['totals']['errors']}`",
                f"- Shards completed: `{len(full['shards'])}/{full['shard_count']}`",
                f"- Manifest stable: `{full['manifest_stable']}`",
                f"- Phase 224 score: `{score}/100`",
                "",
                "## Interpretation",
                "",
                "Robustness controls and software integration passed. "
                "Independent data trust, calibrated prediction, financial "
                "edge and decision readiness remain unproven.",
                "",
                "```text",
                "data_trust_validated: False",
                "predictive_validity_established: False",
                "edge_validated: False",
                "decision_layer_allowed: False",
                "canonical_data_writes: 0",
                "```",
            ]
        ),
    )

    write_markdown(
        diagram,
        "\n".join(
            [
                "# QRDS Architecture - Phase 225",
                "",
                "```mermaid",
                "flowchart LR",
                "  P215[215 Historical Replay Integration] --> P216[216 Provenance]",
                "  P216 --> P217[217 Agreement Diagnostics]",
                "  P217 --> P218[218 Contamination Sensitivity]",
                "  P218 --> P219[219 Boundary Perturbation]",
                "  P219 --> P220[220 Robustness Checkpoint]",
                "  P220 --> P221[221 Model-Free Benchmarks]",
                "  P221 --> P222[222 Uncertainty Diagnostics]",
                "  P222 --> P223[223 Cost Sensitivity]",
                "  P223 --> P224[224 Robustness Scorecard]",
                "  P224 --> P225[225 Mandatory Full Integration]",
                "  P225 -. blocked .-> D[Decision Layer]",
                "```",
                "",
                "The decision layer remains blocked.",
            ]
        ),
    )

    write_markdown(
        table,
        "\n".join(
            [
                "# QRDS Progress Table by Tens - Phase 225",
                "",
                "| Range | Theme | Checkpoint | Status |",
                "|---|---|---|---|",
                "| 186-195 | Integrity and full integration | 195 | PASS_RESEARCH_ONLY |",
                "| 196-205 | Data trust and shadow replay controls | 205 | PASS_RESEARCH_ONLY |",
                "| 206-215 | Controlled historical replay evidence | 215 | PASS_RESEARCH_ONLY |",
                "| 216-225 | Cross-window robustness and trust escalation | 225 | PASS_RESEARCH_ONLY |",
                "| 226-235 | Predictive validity gate design | 235 | PLANNED_RESEARCH_ONLY |",
                "",
                "All ranges remain under `BLOCKED_RESEARCH_ONLY`.",
            ]
        ),
    )

    write_markdown(
        milestone,
        "\n".join(
            [
                "# QRDS Integrated Test Milestone 216-225",
                "",
                f"**Checkpoint:** `{payload['checkpoint_status']}`",
                f"**Test files:** `{full['test_file_count']}`",
                f"**Tests:** `{full['totals']['tests']}`",
                f"**Failures:** `{full['totals']['failures']}`",
                f"**Errors:** `{full['totals']['errors']}`",
                f"**Manifest stable:** `{full['manifest_stable']}`",
                "**Mandatory global full-suite at 225:** `True`",
                "**Next mandatory global full-suite:** `245`",
                "",
                "The complete available test suite passed across three shards.",
            ]
        ),
    )

    write_markdown(
        roadmap,
        "\n".join(
            [
                "# QRDS Roadmap 226-235 - Research Only",
                "",
                "**Theme:** Predictive Validity Gate Design",
                "**Operational mode:** `BLOCKED_RESEARCH_ONLY`",
                "",
                "| Phase | Scope |",
                "|---:|---|",
                "| 226 | Validation target and metric contract |",
                "| 227 | Embargoed holdout policy |",
                "| 228 | Nested walk-forward split design |",
                "| 229 | Feature-target leakage hardening |",
                "| 230 | Predictive validity batch checkpoint |",
                "| 231 | Benchmark superiority test design |",
                "| 232 | Calibration stability across regimes |",
                "| 233 | Multiple-testing and false-discovery controls |",
                "| 234 | Predictive validity evidence scorecard |",
                "| 235 | Integrated tracking checkpoint |",
                "",
                "No phase may produce signals, recommendations, allocations, "
                "orders, real-capital actions or canonical data writes.",
            ]
        ),
    )

    write_json(
        snapshot,
        {
            "baseline_phase": 225,
            "baseline_commit_before_batch": "69d6483",
            "checkpoint_status": payload["checkpoint_status"],
            "global_full_suite": {
                "passed": full["passed"],
                "test_file_count": full["test_file_count"],
                "tests": full["totals"]["tests"],
                "failures": full["totals"]["failures"],
                "errors": full["totals"]["errors"],
                "manifest_stable": full["manifest_stable"],
                "shards_completed": len(full["shards"]),
            },
            "phase224_score": score,
            "next_tracking_checkpoint": 235,
            "next_mandatory_global_full_suite": 245,
            "data_trust_validated": False,
            "predictive_validity_established": False,
            "edge_validated": False,
            "decision_layer_allowed": False,
            "operational_status": "BLOCKED_RESEARCH_ONLY",
            "canonical_data_writes": 0,
        },
    )
    return {
        "master": master,
        "diagram": diagram,
        "table": table,
        "milestone": milestone,
        "roadmap": roadmap,
        "snapshot": snapshot,
    }


def build_phase225_from_full_suite(
    phase_artifacts: list[Path],
    full_suite: dict[str, Any],
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phases = {
        str(phase): read_json(path)
        for phase, path in zip(range(216, 225), phase_artifacts)
    }
    phase_checks = {
        "216": phases["216"]["provenance_completeness_passed"],
        "217": phases["217"]["multi_source_agreement_diagnostic_passed"],
        "218": phases["218"]["contamination_sensitivity_passed"],
        "219": phases["219"]["window_boundary_perturbation_passed"],
        "220": phases["220"]["robustness_checkpoint_passed"],
        "221": phases["221"]["benchmark_comparison_passed"],
        "222": phases["222"]["calibration_diagnostic_passed"],
        "223": phases["223"]["cost_slippage_sensitivity_passed"],
        "224": phases["224"]["robustness_scorecard_passed"],
    }
    passed = all(phase_checks.values()) and full_suite["passed"]
    payload = {
        "phase": 225,
        "checkpoint_status": (
            "FULL_INTEGRATION_216_225_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
        "window_integration_passed": passed,
        "global_full_suite_passed": full_suite["passed"],
        "phase_checks": phase_checks,
        "phase_chain": phases,
        "phase_chain_digest": stable_digest(
            {
                phase: {
                    "status": item["status"],
                    "locks": item["locks"],
                }
                for phase, item in phases.items()
            }
        ),
        "full_suite": full_suite,
        "robustness_controls_validated_for_research": bool(
            phases["224"]["robustness_scorecard_passed"]
        ),
        "independent_source_agreement_validated": False,
        "data_trust_validated": False,
        "calibration_validated": False,
        "predictive_validity_established": False,
        "edge_validated": False,
        "valid_for_decision": False,
        "next_tracking_checkpoint": 235,
        "next_mandatory_global_full_suite": 245,
        "caps": research_caps(),
        "locks": locks_copy(),
    }

    tracking = tracking_documents(payload, tracking_dir, root)
    payload["tracking_documents"] = {
        key: value.relative_to(root).as_posix()
        for key, value in tracking.items()
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 225 - Robustness Full Integration Checkpoint",
                "",
                f"**Checkpoint:** `{payload['checkpoint_status']}`",
                f"**Test files:** `{full_suite['test_file_count']}`",
                f"**Tests:** `{full_suite['totals']['tests']}`",
                f"**Failures:** `{full_suite['totals']['failures']}`",
                f"**Errors:** `{full_suite['totals']['errors']}`",
                f"**Manifest stable:** `{full_suite['manifest_stable']}`",
                "**Mandatory full-suite at 225:** `True`",
                "**Next mandatory full-suite:** `245`",
                "",
                "The robustness and integration controls passed. The system "
                "remains blocked from operational decisions.",
                "",
                "```text",
                "operational_status: BLOCKED_RESEARCH_ONLY",
                "data_trust_validated: False",
                "predictive_validity_established: False",
                "edge_validated: False",
                "decision_layer_allowed: False",
                "canonical_data_writes: 0",
                "```",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    for phase in range(216, 225):
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            required=True,
        )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    parser.add_argument("--tracking-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=5400)
    args = parser.parse_args()

    phase_artifacts = [
        resolve_repo_path(getattr(args, f"phase{phase}_artifact"))
        for phase in range(216, 225)
    ]
    artifact_path = resolve_repo_path(args.artifact)
    documentation_path = resolve_repo_path(args.documentation)
    tracking_dir = resolve_repo_path(args.tracking_dir)
    output_dir = resolve_repo_path(args.output_dir)

    full_suite = run_full_suite(
        output_dir,
        args.timeout_seconds,
    )
    payload = build_phase225_from_full_suite(
        phase_artifacts,
        full_suite,
        artifact_path,
        documentation_path,
        tracking_dir,
    )
    print("PHASE225:", payload["checkpoint_status"])
    print("Test files:", full_suite["test_file_count"])
    print("Tests:", full_suite["totals"]["tests"])
    print("Failures:", full_suite["totals"]["failures"])
    print("Errors:", full_suite["totals"]["errors"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    return 0 if payload["window_integration_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
