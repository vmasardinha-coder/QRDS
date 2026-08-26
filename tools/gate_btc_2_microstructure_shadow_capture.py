#!/usr/bin/env python3
"""One-shot Stage 9 forward capture with a fail-closed GitHub schedule gate."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.gate_btc_2_microstructure_shadow_contract import assess, load_json
from tools.gate_btc_2_microstructure_shadow_manifest import (
    DEFAULT_CONTRACT,
    RECEIPT_SCHEMA,
    SPECS,
    build_manifest,
    iso_utc,
    validate_environment,
)


Fetch = Callable[[str, dict[str, str]], bytes]
MAX_RESPONSE_BYTES = 2_000_000
DECISION_SCHEMA = "gate_btc.2_0.microstructure_shadow_capture_decision.v1"
WORKFLOW_NAME = "GATE BTC 2 Microstructure Shadow Manual Capture"


def fetch_bytes(url: str, headers: dict[str, str], timeout: int = 25) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"non-200 response from {url}")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"response size outside admission boundary: {url}")
    return raw


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_bytes(raw)
    os.replace(partial, path)


def active_runs(
    repository: str,
    token: str,
    current_run_id: int,
    fetcher: Fetch = fetch_bytes,
) -> list[dict[str, Any]]:
    if not repository or "/" not in repository:
        raise ValueError("repository must use owner/name form")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GATE-BTC-2-stage9-schedule-gate/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    runs: dict[int, dict[str, Any]] = {}
    for status in ("in_progress", "queued"):
        url = f"https://api.github.com/repos/{repository}/actions/runs?status={status}&per_page=100"
        try:
            payload = json.loads(fetcher(url, headers))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("GitHub active-run response is not valid JSON") from exc
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("workflow_runs"), list)
            or not isinstance(payload.get("total_count"), int)
            or isinstance(payload.get("total_count"), bool)
        ):
            raise RuntimeError("GitHub active-run response has unexpected schema")
        if payload["total_count"] != len(payload["workflow_runs"]):
            raise RuntimeError("GitHub active-run response requires pagination; capture blocked")
        for row in payload["workflow_runs"]:
            if not isinstance(row, dict) or not isinstance(row.get("id"), int):
                raise RuntimeError("GitHub active-run row has unexpected schema")
            if row["id"] == current_run_id:
                continue
            if not all(isinstance(row.get(key), str) for key in ("name", "event", "status")):
                raise RuntimeError("GitHub active-run identity is incomplete")
            runs[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "event": row["event"],
                "status": row["status"],
            }
    return sorted(runs.values(), key=lambda row: (row["name"], row["id"]))


def safety_fields() -> dict[str, Any]:
    return {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run_capture(
    output_dir: Path,
    repository: str,
    current_run_id: int,
    token: str = "",
    fetcher: Fetch = fetch_bytes,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    validate_environment()
    contract = load_json(contract_path)
    observed = active_runs(repository, token, current_run_id, fetcher)
    names = sorted({row["name"] for row in observed})
    preflight = assess(contract, active_workflows=names)
    scheduled = [row for row in observed if row["event"] == "schedule"]
    duplicate_manual = [row for row in observed if row["name"] == WORKFLOW_NAME]
    protected = preflight["protected_active_workflows"]
    checked_at = now()
    if checked_at.tzinfo is None:
        raise ValueError("capture clock must be timezone-aware")

    decision: dict[str, Any] = {
        "schema": DECISION_SCHEMA,
        "checked_at_utc": iso_utc(checked_at),
        "repository": repository,
        "current_run_id": current_run_id,
        "active_or_queued_runs": observed,
        "protected_active_workflows": protected,
        "scheduled_active_or_queued_runs": scheduled,
        "other_manual_capture_runs": duplicate_manual,
        "active_workflows_checked": True,
        "market_network_requests": 0,
        **safety_fields(),
    }
    decision_path = output_dir / "capture_decision.json"
    if preflight["status"] == "BLOCKED_INVALID_CONTRACT":
        decision["status"] = "BLOCKED_INVALID_CONTRACT"
        decision["contract_errors"] = preflight["contract_errors"]
        atomic_write(decision_path, (json.dumps(decision, indent=2, sort_keys=True) + "\n").encode())
        return decision
    if protected or scheduled or duplicate_manual:
        decision["status"] = "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW"
        atomic_write(decision_path, (json.dumps(decision, indent=2, sort_keys=True) + "\n").encode())
        return decision

    raw_dir = output_dir / "raw"
    receipt_sources = []
    for role in contract["required_source_roles"]:
        spec = SPECS[role]
        raw = fetcher(spec["url"], {"User-Agent": "GATE-BTC-2-stage9-forward-capture/1.0"})
        if not raw or len(raw) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"{role} response size outside admission boundary")
        captured = now()
        if captured.tzinfo is None:
            raise ValueError("capture clock must be timezone-aware")
        atomic_write(raw_dir / spec["raw_file"], raw)
        receipt_sources.append({
            "source_role": role,
            "raw_file": spec["raw_file"],
            "request_url": spec["url"],
            "captured_at_utc": iso_utc(captured),
        })

    created = now()
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "capture_id": f"gate2-stage9-run-{current_run_id}",
        "created_at_utc": iso_utc(created),
        "contract_sha256": contract["contract_sha256"],
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "network_capture_job_count": 1,
        "sources": receipt_sources,
    }
    receipt_path = output_dir / "capture_receipt.json"
    atomic_write(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    manifest = build_manifest(receipt, raw_dir, contract)
    manifest_path = output_dir / "capture_manifest.json"
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())

    decision.update({
        "status": "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW",
        "capture_id": receipt["capture_id"],
        "market_network_requests": len(receipt_sources),
        "required_source_roles_captured": [row["source_role"] for row in receipt_sources],
        "shadow_feeds_reconciled": False,
    })
    atomic_write(decision_path, (json.dumps(decision, indent=2, sort_keys=True) + "\n").encode())
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    decision = run_capture(
        args.output_dir,
        args.repository,
        args.run_id,
        token=os.environ.get("GITHUB_TOKEN", ""),
        contract_path=args.contract,
    )
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
