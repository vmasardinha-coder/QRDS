#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone

ACTIVE_STATUSES = {"queued", "in_progress", "waiting", "pending", "requested"}
DEFAULT_FRESHNESS_SECONDS = 900


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def dispatch_decision(runs, now: datetime, freshness_seconds: int = DEFAULT_FRESHNESS_SECONDS):
    now = now.astimezone(timezone.utc)
    active = [run for run in runs if run.get("status") in ACTIVE_STATUSES]
    if active:
        newest = max(active, key=lambda run: run.get("created_at", ""))
        return False, f"ACTIVE run_id={newest.get('id')} status={newest.get('status')}"

    successful = [
        run for run in runs
        if run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and (run.get("updated_at") or run.get("created_at"))
    ]
    if successful:
        newest = max(successful, key=lambda run: run.get("updated_at") or run.get("created_at", ""))
        stamp = parse_utc(newest.get("updated_at") or newest["created_at"])
        age = max(0.0, (now - stamp).total_seconds())
        if age < freshness_seconds:
            return False, f"FRESH_SUCCESS run_id={newest.get('id')} age_seconds={int(age)}"

    return True, "STALE_OR_NO_SUCCESS"


def github_json(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gate-btc-crypto-forward-schedule-guard",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def dispatch(repository: str, workflow: str, token: str):
    url = f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/dispatches"
    payload = json.dumps({"ref": "main"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gate-btc-crypto-forward-schedule-guard",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 204:
            raise RuntimeError(f"unexpected dispatch status={response.status}")


def main():
    token = os.environ["GH_TOKEN"]
    repository = os.environ["REPOSITORY"]
    workflow = os.environ.get("TARGET_WORKFLOW", "gate-btc-crypto-forward-public-capture.yml")
    freshness = int(os.environ.get("FRESHNESS_SECONDS", str(DEFAULT_FRESHNESS_SECONDS)))
    runs_url = (
        f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/runs"
        "?branch=main&per_page=30"
    )
    runs = github_json(runs_url, token).get("workflow_runs", [])
    should_dispatch, reason = dispatch_decision(runs, datetime.now(timezone.utc), freshness)
    if not should_dispatch:
        print(f"CRYPTO_FORWARD_FALLBACK=NOT_NEEDED reason={reason}")
        return
    dispatch(repository, workflow, token)
    print(f"CRYPTO_FORWARD_FALLBACK=DISPATCHED reason={reason} freshness_seconds={freshness}")


if __name__ == "__main__":
    main()
