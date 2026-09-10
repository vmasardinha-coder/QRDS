#!/usr/bin/env python3
"""Wake the Delta paper monitor for a collection the fallback itself dispatched.

The daily fallback recovers a missed or failed Daily Research collection by
dispatching it through the API with GITHUB_TOKEN. That recovery works, and it is
also what breaks the monitor: GitHub does not emit `workflow_run` for a run
dispatched with GITHUB_TOKEN, so the collection succeeds and nothing downstream
ever hears about it. On 2026-09-09 and again on 2026-09-10 the V11 series stalled
for exactly this reason and a person had to dispatch the monitor by hand.

The entity that opens the hole is the one that closes it: after dispatching the
collection, the fallback waits for it and, only if it succeeded, wakes the
monitor with that run id.

Waking is all this does. Whether the close may be appended stays the monitor's
judgement — it verifies a repeated day against the recorded row hashes and
refuses a gap outright, and neither rule is duplicated or softened here.

The HTTP call is injected so the policy is testable without a network.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from typing import Any, Callable

SCHEMA = "gate_btc.daily_fallback_wake.v1"

MONITOR_WORKFLOW = "gate-btc-delta-paper-monitor.yml"
COLLECTION_WORKFLOW = "gate-btc-daily-research.yml"

WOKE = "WOKE_MONITOR"
NOT_SUCCESSFUL = "COLLECTION_NOT_SUCCESSFUL"
NO_RUN_FOUND = "NO_DISPATCHED_RUN_FOUND"
STILL_RUNNING = "COLLECTION_STILL_RUNNING_AT_DEADLINE"

TERMINAL = {"completed"}


class WakeError(RuntimeError):
    pass


def github(token: str) -> Callable[..., Any]:
    """Return a caller that speaks the GitHub REST API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gate-btc-daily-fallback-wake",
    }

    def call(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=30) as response:
            if method == "POST":
                if response.status != 204:
                    raise WakeError(f"unexpected dispatch status={response.status}")
                return None
            return json.load(response)

    return call


def newest_dispatched_run(api: Callable[..., Any], repository: str, after: str) -> dict[str, Any] | None:
    """The most recent workflow_dispatch collection run created at or after `after`.

    The fallback cannot know the id of the run it just triggered — the dispatch
    endpoint returns no body — so it is identified by being a dispatch run newer
    than the moment the fallback asked for one.
    """
    url = (f"https://api.github.com/repos/{repository}/actions/workflows/"
           f"{COLLECTION_WORKFLOW}/runs?branch=main&event=workflow_dispatch&per_page=10")
    runs = api("GET", url).get("workflow_runs", [])
    fresh = [r for r in runs if str(r.get("created_at", "")) >= after]
    if not fresh:
        return None
    return max(fresh, key=lambda r: str(r.get("created_at", "")))


def should_wake(run: dict[str, Any] | None) -> tuple[bool, str]:
    """Only a completed, successful collection is worth waking the monitor for."""
    if run is None:
        return False, NO_RUN_FOUND
    if run.get("status") not in TERMINAL:
        return False, STILL_RUNNING
    if run.get("conclusion") != "success":
        return False, NOT_SUCCESSFUL
    return True, WOKE


def wait_for_run(api: Callable[..., Any], repository: str, after: str,
                 attempts: int = 40, delay: float = 30.0,
                 sleep: Callable[[float], None] = time.sleep) -> dict[str, Any] | None:
    """Poll until the dispatched collection reaches a terminal state or we give up."""
    run = None
    for attempt in range(attempts):
        run = newest_dispatched_run(api, repository, after)
        if run is not None and run.get("status") in TERMINAL:
            return run
        if attempt < attempts - 1:
            sleep(delay)
    return run


def wake(api: Callable[..., Any], repository: str, run_id: int) -> None:
    url = (f"https://api.github.com/repos/{repository}/actions/workflows/"
           f"{MONITOR_WORKFLOW}/dispatches")
    api("POST", url, {"ref": "main", "inputs": {"run_id": str(run_id)}})


def run(api: Callable[..., Any], repository: str, after: str, **kw: Any) -> dict[str, Any]:
    collection = wait_for_run(api, repository, after, **kw)
    ok, status = should_wake(collection)
    result = {
        "schema": SCHEMA,
        "status": status,
        "collection_run_id": collection.get("id") if collection else None,
        "collection_conclusion": collection.get("conclusion") if collection else None,
    }
    if ok:
        wake(api, repository, int(collection["id"]))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--after", required=True,
                        help="ISO instant; only dispatch runs at or after it are considered")
    parser.add_argument("--attempts", type=int, default=40)
    parser.add_argument("--delay", type=float, default=30.0)
    args = parser.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise WakeError("no GH_TOKEN in the environment")
    if not args.repository:
        raise WakeError("no repository given")

    result = run(github(token), args.repository, args.after,
                 attempts=args.attempts, delay=args.delay)
    print(json.dumps(result, indent=2, sort_keys=True))
    # A collection that failed is not this tool's failure: the fallback already
    # reported the dispatch, and the collection's own run carries the red.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
