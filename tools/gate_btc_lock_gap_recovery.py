#!/usr/bin/env python3
"""Recover missing LOCK25/50 closes from immutable successful Daily Research artifacts.

This is an evidence-transport repair only.  It never synthesizes a return, uses a
future artifact for an earlier close, changes a portfolio, or bypasses the
append-only LOCK ledger.  Every recovered close is rebuilt from the Daily
Research artifact whose embedded V2A manifest has that exact data_as_of date.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import tempfile
import urllib.request
import urllib.parse
import zipfile
from datetime import date, timedelta
from pathlib import Path

WORKFLOW_NAME = "GATE BTC Daily Research Collection"
RUNTIME_SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
}


def missing_dates(latest: str | None, first: str, target_exclusive: str) -> list[str]:
    first_day = date.fromisoformat(first)
    target = date.fromisoformat(target_exclusive)
    start = date.fromisoformat(latest) + timedelta(days=1) if latest else first_day
    if start < first_day:
        start = first_day
    out = []
    while start < target:
        out.append(start.isoformat())
        start += timedelta(days=1)
    return out


def _request_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gate-btc-lock-gap-recovery",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


class _StripAuthOnCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Keep GitHub API auth off the signed artifact-storage redirect.

    GitHub's artifact download endpoint redirects to a short-lived signed blob URL.
    urllib's default redirect handling forwards the Authorization header to that
    different host; Azure/S3 rejects the otherwise-valid signed request with 401.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        old_host = urllib.parse.urlsplit(req.full_url).netloc.lower()
        new_host = urllib.parse.urlsplit(newurl).netloc.lower()
        if old_host != new_host:
            redirected.remove_header("Authorization")
        return redirected


def _request_bytes(url: str, token: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gate-btc-lock-gap-recovery",
    })
    opener = urllib.request.build_opener(_StripAuthOnCrossHostRedirect())
    with opener.open(req, timeout=120) as r:
        return r.read()


def _embedded_v2a(artifact_bytes: bytes) -> tuple[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as outer:
        names = outer.namelist()
        candidates = [n for n in names if n.endswith("qos_daily/qos_v2a_outputs.zip") or n == "qos_daily/qos_v2a_outputs.zip"]
        if len(candidates) != 1:
            raise RuntimeError(f"expected exactly one qos_v2a_outputs.zip, got {candidates}")
        nested = outer.read(candidates[0])
    with zipfile.ZipFile(io.BytesIO(nested)) as inner:
        manifests = [n for n in inner.namelist() if n.endswith("outputs/v2a_run_manifest.json")]
        if len(manifests) != 1:
            raise RuntimeError(f"expected one v2a manifest, got {manifests}")
        manifest = json.loads(inner.read(manifests[0]).decode("utf-8-sig"))
        if manifest.get("research_only") is not True:
            raise RuntimeError("V2A source is not research_only")
        if manifest.get("operational_status") != "NOT_APPROVED":
            raise RuntimeError("V2A source is not NOT_APPROVED")
        return str(manifest["data_as_of"]), nested


def _successful_runs(repo: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/actions/workflows/gate-btc-daily-research.yml/runs?branch=main&status=success&per_page=100"
    payload = _request_json(url, token)
    runs = []
    for run in payload.get("workflow_runs", []):
        if (run.get("name") == WORKFLOW_NAME and run.get("head_branch") == "main"
                and run.get("status") == "completed" and run.get("conclusion") == "success"):
            runs.append(run)
    return runs


def _artifact_for_run(repo: str, token: str, run_id: int) -> bytes | None:
    payload = _request_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100", token)
    artifacts = [a for a in payload.get("artifacts", [])
                 if not a.get("expired") and str(a.get("name", "")).startswith("gate-btc-daily-research-")]
    if len(artifacts) != 1:
        return None
    return _request_bytes(artifacts[0]["archive_download_url"], token)


def recover(args: argparse.Namespace) -> dict:
    status_path = args.ledger_dir / "STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    latest = status.get("latest_snapshot_id")
    dates = missing_dates(latest, args.first_eligible_close, args.target_exclusive)
    if not dates:
        return {"status": "NO_GAP", "recovered": [], **RUNTIME_SAFETY}

    token = args.token or os.environ.get("GH_TOKEN", "")
    if not token:
        raise RuntimeError("GitHub token required for immutable artifact recovery")
    runs = _successful_runs(args.repo, token)
    by_date: dict[str, tuple[int, bytes]] = {}
    needed = set(dates)
    for run in runs:
        if not needed:
            break
        raw = _artifact_for_run(args.repo, token, int(run["id"]))
        if raw is None:
            continue
        try:
            data_as_of, nested = _embedded_v2a(raw)
        except Exception:
            continue
        if data_as_of in needed and data_as_of not in by_date:
            by_date[data_as_of] = (int(run["id"]), nested)
            needed.remove(data_as_of)
    if needed:
        raise RuntimeError(f"immutable successful Daily Research artifact missing for closes={sorted(needed)}")

    recovered = []
    for close in dates:
        run_id, nested = by_date[close]
        with tempfile.TemporaryDirectory(prefix=f"gate-btc-lock-{close}-") as td:
            root = Path(td)
            with zipfile.ZipFile(io.BytesIO(nested)) as zf:
                zf.extractall(root)
            master = next(root.glob("**/data/processed/qos_v2a_master_daily.csv"), None)
            portfolios = next(root.glob("**/outputs/qos_v2a_current_portfolios.csv"), None)
            if master is None or portfolios is None:
                raise RuntimeError(f"required V2A files absent for {close}")
            subprocess.run([
                args.python, "tools/gate_btc_measurement_ledgers.py", "append-lock",
                "--contract", str(args.contract),
                "--master-daily", str(master),
                "--current-portfolios", str(portfolios),
                "--snapshot-id", close,
                "--cycle-id", args.cycle_id,
                "--ledger-dir", str(args.ledger_dir),
            ], check=True)
        recovered.append({"date": close, "source_run_id": run_id})
    return {"status": "RECOVERED_IMMUTABLE_GAP", "recovered": recovered, **RUNTIME_SAFETY}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--first-eligible-close", required=True)
    p.add_argument("--target-exclusive", required=True)
    p.add_argument("--token", default="")
    p.add_argument("--python", default="python")
    a = p.parse_args()
    result = recover(a)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
