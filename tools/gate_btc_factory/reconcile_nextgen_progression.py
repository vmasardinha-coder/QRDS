#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "tools/gate_btc_factory/FACTORY_TRANSITIONS_RUNTIME.json"
ACTIVE = {"in_progress", "queued", "waiting", "requested", "pending"}


@dataclass(frozen=True)
class Stage:
    name: str
    workflow: str


STAGES = (
    Stage("STAGE0", "gate-btc-b3-h-nextgen-stage0.yml"),
    Stage("STAGE1", "gate-btc-b3-h-stage1-adapter.yml"),
    Stage("STAGE2_FALSIFICATION", "gate-btc-b3-h-stage2-falsification.yml"),
    Stage("STAGE2B_REPLICATION", "gate-btc-b3-h-stage2b-replication.yml"),
    Stage("FINAL", "gate-btc-b3-h-nextgen-final.yml"),
)


def run_json(args: list[str]) -> object:
    proc = subprocess.run(args, check=True, text=True, capture_output=True)
    text = proc.stdout.strip()
    return json.loads(text) if text else None


def load_runtime_frontier() -> dict | None:
    try:
        raw = subprocess.check_output(
            ["git", "show", "origin/gate-btc-runtime:runtime/autonomous_science/CURRENT.json"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"FAIL_CLOSED malformed canonical runtime frontier: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("FAIL_CLOSED canonical runtime frontier is not an object")
    return value


def load_plan() -> dict:
    try:
        value = json.loads(PLAN.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL_CLOSED cannot read transition plan: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("FAIL_CLOSED transition plan is not an object")
    return value


def target_from_authorities() -> tuple[str, str] | None:
    frontier = load_runtime_frontier()
    if not frontier:
        print("NEXTGEN_PROGRESS=FAIL_CLOSED_NO_RUNTIME_FRONTIER")
        return None

    generation = str(frontier.get("generation") or "")
    status = str(frontier.get("status") or "")
    survivors = frontier.get("survivors") or []
    try:
        next_start = int(frontier.get("next_generation_start"))
    except (TypeError, ValueError):
        print("NEXTGEN_PROGRESS=FAIL_CLOSED_BAD_NEXT_GENERATION_START")
        return None

    if not generation or "CLOSED" not in status or "NO_" not in status or "SURVIVOR" not in status:
        print(f"NEXTGEN_PROGRESS=NO_CLOSED_NULL_FRONTIER:{generation}:{status}")
        return None
    if survivors:
        print(f"NEXTGEN_PROGRESS=FAIL_CLOSED_SURVIVOR_PRESENT:{generation}")
        return None
    if next_start <= 0:
        print("NEXTGEN_PROGRESS=FAIL_CLOSED_NONPOSITIVE_NEXT_GENERATION_START")
        return None

    next_generation = f"H{next_start}-H{next_start + 9}"
    marker = f"B3 {next_generation}"
    plan = load_plan()
    actions = plan.get("actions", [])
    authorized = any(
        isinstance(action, dict)
        and action.get("action") == "CREATE_NEXT_GENERATION_ISSUE"
        and action.get("marker") == marker
        for action in actions
    )
    if plan.get("source_freshness") != "FRESH" or plan.get("transitions_allowed") is not True or not authorized:
        print(f"NEXTGEN_PROGRESS=FAIL_CLOSED_TARGET_NOT_AUTHORIZED:{marker}")
        return None

    frontier_key = f"{generation}__NEXT_{next_generation}"
    return frontier_key, next_generation


def latest(repo: str, stage: Stage, *, frontier_key: str | None = None) -> dict | None:
    fields = "databaseId,status,conclusion,createdAt,headSha,displayTitle"
    rows = run_json([
        "gh", "run", "list",
        "--repo", repo,
        "--workflow", stage.workflow,
        "--branch", "main",
        "--limit", "20" if frontier_key else "1",
        "--json", fields,
    ])
    if not isinstance(rows, list) or not rows:
        return None
    if frontier_key is None:
        row = rows[0]
        return row if isinstance(row, dict) else None
    expected = f"B3 NextGen {frontier_key}"
    for row in rows:
        if isinstance(row, dict) and row.get("displayTitle") == expected:
            return row
    return None


def active_count(repo: str, stage: Stage) -> int:
    rows = run_json([
        "gh", "run", "list",
        "--repo", repo,
        "--workflow", stage.workflow,
        "--branch", "main",
        "--limit", "20",
        "--json", "status",
    ])
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if isinstance(row, dict) and row.get("status") in ACTIVE)


def completed_success(row: dict | None) -> bool:
    return bool(row and row.get("status") == "completed" and row.get("conclusion") == "success")


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY") or os.environ.get("GH_REPO")
    if not repo:
        raise SystemExit("FAIL_CLOSED missing GITHUB_REPOSITORY/GH_REPO")

    target = target_from_authorities()
    if target is None:
        return 0
    frontier_key, next_generation = target

    anchor = latest(repo, STAGES[0], frontier_key=frontier_key)
    if anchor is None:
        if active_count(repo, STAGES[0]):
            print(f"NEXTGEN_PROGRESS=SINGLE_FLIGHT:{STAGES[0].name}")
            return 0
        subprocess.run([
            "gh", "workflow", "run", STAGES[0].workflow,
            "--repo", repo,
            "--ref", "main",
            "-f", f"frontier_key={frontier_key}",
            "-f", f"next_generation={next_generation}",
        ], check=True)
        print(f"NEXTGEN_PROGRESS=DISPATCHED_FRONTIER_STAGE0:{frontier_key}")
        return 0
    if anchor.get("status") in ACTIVE:
        print(f"NEXTGEN_PROGRESS=WAIT_ACTIVE:{STAGES[0].name}:{anchor.get('databaseId')}")
        return 0
    if not completed_success(anchor):
        print(
            "NEXTGEN_PROGRESS=FAIL_CLOSED_PREDECESSOR:"
            f"{STAGES[0].name}:{anchor.get('conclusion')}:{anchor.get('databaseId')}"
        )
        return 0

    predecessor = anchor
    predecessor_stage = STAGES[0]

    for stage in STAGES[1:]:
        current = latest(repo, stage)
        pred_time = str(predecessor.get("createdAt") or "")
        cur_time = str((current or {}).get("createdAt") or "")
        belongs_to_chain = bool(current and cur_time >= pred_time)

        if not belongs_to_chain:
            if active_count(repo, stage):
                print(f"NEXTGEN_PROGRESS=SINGLE_FLIGHT:{stage.name}")
                return 0
            subprocess.run([
                "gh", "workflow", "run", stage.workflow,
                "--repo", repo,
                "--ref", "main",
            ], check=True)
            print(
                "NEXTGEN_PROGRESS=DISPATCHED:"
                f"{predecessor_stage.name}->{stage.name}:"
                f"predecessor_run={predecessor.get('databaseId')}"
            )
            return 0

        if current.get("status") in ACTIVE:
            print(f"NEXTGEN_PROGRESS=WAIT_ACTIVE:{stage.name}:{current.get('databaseId')}")
            return 0

        if not completed_success(current):
            print(
                "NEXTGEN_PROGRESS=FAIL_CLOSED_STAGE:"
                f"{stage.name}:{current.get('conclusion')}:{current.get('databaseId')}"
            )
            return 0

        predecessor = current
        predecessor_stage = stage

    print(f"NEXTGEN_PROGRESS=CHAIN_COMPLETE:{frontier_key}:final_run={predecessor.get('databaseId')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
