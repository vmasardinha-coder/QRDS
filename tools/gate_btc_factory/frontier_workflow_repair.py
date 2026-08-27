#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/gate_btc_factory/FRONTIER_REPAIR_RUNTIME.json"

EXACT_WORKFLOWS = {
    "GATE BTC B3 H NextGen Stage0",
    "GATE BTC B3 H Stage1 Adapter",
    "GATE BTC B3 H Stage2 Falsification",
    "GATE BTC B3 H Stage2B Replication",
    "GATE BTC B3 H NextGen Final",
}

FAMILY_WORKFLOW_RE = re.compile(r"^GATE BTC B3 H\d+-H\d+ .*?(?:Source QA|Stage0|Adapter|Qualification)$", re.I)
OPERATIONAL_STEP_RE = re.compile(
    r"(?:probe|source|network|fetch|download|schema|adapter|plumbing|contract|setup|checkout|install|artifact)",
    re.I,
)
SCIENTIFIC_STEP_RE = re.compile(
    r"(?:economics|falsification result|replication result|survivor|promotion|approve|retune|threshold|cutoff)",
    re.I,
)


def gh_json(path: str) -> dict:
    cp = subprocess.run(["gh", "api", path], check=True, text=True, capture_output=True)
    return json.loads(cp.stdout)


def latest_candidate_runs(repo: str) -> list[dict]:
    data = gh_json(f"repos/{repo}/actions/runs?per_page=100")
    runs = data.get("workflow_runs", [])
    selected: dict[tuple[str, str], dict] = {}
    for run in runs:
        name = str(run.get("name", ""))
        if name not in EXACT_WORKFLOWS and not FAMILY_WORKFLOW_RE.search(name):
            continue
        key = (name, str(run.get("head_branch", "")))
        if key not in selected:
            selected[key] = run
    return list(selected.values())


def failed_steps(repo: str, run_id: int) -> list[str]:
    data = gh_json(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    out: list[str] = []
    for job in data.get("jobs", []):
        for step in job.get("steps", []):
            if step.get("conclusion") == "failure":
                out.append(str(step.get("name", "")))
    return out


def classify(run: dict, steps: list[str]) -> tuple[str, str]:
    if run.get("status") != "completed":
        return "ACTIVE", "single-flight"
    if run.get("conclusion") == "success":
        return "HEALTHY", "latest run successful"
    if run.get("conclusion") != "failure":
        return "NO_ACTION", f"conclusion={run.get('conclusion')}"
    attempt = int(run.get("run_attempt") or 1)
    if attempt >= 2:
        return "PERSISTENT_BLOCKER", "bounded retry already consumed"
    if not steps:
        return "PERSISTENT_BLOCKER", "failure has no classifiable failed step"
    if any(SCIENTIFIC_STEP_RE.search(s) for s in steps):
        return "FAIL_CLOSED_SCIENCE", "scientific/result-bearing failure"
    if all(OPERATIONAL_STEP_RE.search(s) for s in steps):
        return "RETRY_FAILED_JOBS_ONCE", "operational/source/plumbing failure"
    return "PERSISTENT_BLOCKER", "unclassified failure; no automatic mutation"


def apply_retry(repo: str, run_id: int) -> None:
    subprocess.run(
        ["gh", "run", "rerun", str(run_id), "--failed", "--repo", repo],
        check=True,
        text=True,
    )


def incident_marker(row: dict) -> str:
    workflow = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(row.get("workflow", "unknown")))
    branch = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(row.get("head_branch", "unknown")))
    return f"FACTORY-FRONTIER-BLOCKER:{workflow}:{branch}"


def ensure_incident(repo: str, row: dict) -> int | None:
    marker = incident_marker(row)
    search = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "open", "--search", marker, "--json", "number,body", "--limit", "100"],
        check=True,
        text=True,
        capture_output=True,
    )
    for issue in json.loads(search.stdout or "[]"):
        if marker in str(issue.get("body", "")):
            return int(issue["number"])
    run_id = int(row["run_id"])
    title = f"Factory frontier blocker: {row.get('workflow')}"
    body = "\n".join(
        [
            f"<!-- {marker} -->",
            "Persistent Factory frontier blocker detected after bounded operational autorepair.",
            "",
            f"- workflow: `{row.get('workflow')}`",
            f"- branch: `{row.get('head_branch')}`",
            f"- run: `{run_id}`",
            f"- attempt: `{row.get('run_attempt')}`",
            f"- action: `{row.get('action')}`",
            f"- reason: `{row.get('reason')}`",
            f"- failed_steps: `{json.dumps(row.get('failed_steps', []), ensure_ascii=False)}`",
            "",
            "Safety boundary: operational diagnosis only. NO_RETUNE, NO_BACKFILL, ORDERS=0, REAL_CAPITAL=0, ENGINE_FEED=false. If scientific authority is required, fail closed.",
        ]
    )
    created = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
        check=True,
        text=True,
        capture_output=True,
    )
    m = re.search(r"/(\d+)\s*$", created.stdout.strip())
    return int(m.group(1)) if m else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo:
        raise SystemExit("FAIL GITHUB_REPOSITORY is required")

    rows = []
    dispatched = []
    incidents = []
    for run in latest_candidate_runs(repo):
        run_id = int(run["id"])
        steps = failed_steps(repo, run_id) if run.get("conclusion") == "failure" else []
        action, reason = classify(run, steps)
        row = {
            "workflow": run.get("name"),
            "head_branch": run.get("head_branch"),
            "run_id": run_id,
            "run_attempt": int(run.get("run_attempt") or 1),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "failed_steps": steps,
            "action": action,
            "reason": reason,
            "scientific_change_allowed": False,
            "backfill_allowed": False,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        }
        if args.apply and action == "RETRY_FAILED_JOBS_ONCE":
            apply_retry(repo, run_id)
            row["action"] = "RETRY_DISPATCHED"
            dispatched.append(run_id)
        elif args.apply and action in {"PERSISTENT_BLOCKER", "FAIL_CLOSED_SCIENCE"}:
            issue_number = ensure_incident(repo, row)
            row["incident_issue"] = issue_number
            if issue_number is not None:
                incidents.append(issue_number)
        rows.append(row)

    report = {
        "schema": "qrds.factory.frontier-workflow-repair.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runs": rows,
        "dispatched_run_ids": dispatched,
        "incident_issue_numbers": sorted(set(incidents)),
        "persistent_blockers": [r for r in rows if r["action"] in {"PERSISTENT_BLOCKER", "FAIL_CLOSED_SCIENCE"}],
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "scientific_change_allowed": False,
            "backfill_allowed": False,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"dispatched": dispatched, "incidents": sorted(set(incidents)), "persistent_blockers": len(report["persistent_blockers"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
