#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass

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


def latest(repo: str, stage: Stage) -> dict | None:
    rows = run_json([
        "gh", "run", "list",
        "--repo", repo,
        "--workflow", stage.workflow,
        "--branch", "main",
        "--limit", "1",
        "--json", "databaseId,status,conclusion,createdAt,headSha",
    ])
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    return row if isinstance(row, dict) else None


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

    anchor = latest(repo, STAGES[0])
    if anchor is None:
        print("NEXTGEN_PROGRESS=NO_STAGE0_ANCHOR")
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

    print(f"NEXTGEN_PROGRESS=CHAIN_COMPLETE:final_run={predecessor.get('databaseId')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
