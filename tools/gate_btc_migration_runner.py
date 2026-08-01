#!/usr/bin/env python3
"""Fail-closed evidence runner for the QRDS/QOS GitHub migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

LOCKS = {"research_only": True, "orders_allowed": False, "orders_generated": 0,
         "real_capital_used": 0, "promotion_allowed": False,
         "operational_status": "NOT_APPROVED"}


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _provenance() -> dict[str, str]:
    checked_out_commit = os.environ.get("GITHUB_SHA") or _git("rev-parse", "HEAD")
    checked_out_ref = os.environ.get("GITHUB_REF_NAME") or _git("branch", "--show-current")
    return {
        "checked_out_commit": checked_out_commit,
        "checked_out_ref": checked_out_ref,
        "source_head_sha": os.environ.get("GATE_BTC_SOURCE_HEAD_SHA") or checked_out_commit,
        "source_head_ref": (
            os.environ.get("GATE_BTC_SOURCE_HEAD_REF")
            or os.environ.get("GITHUB_HEAD_REF")
            or checked_out_ref
        ),
        "base_sha": os.environ.get("GATE_BTC_BASE_SHA", ""),
        "base_ref": os.environ.get("GATE_BTC_BASE_REF", ""),
        "github_event_name": os.environ.get("GITHUB_EVENT_NAME", "LOCAL"),
    }


def run(output_dir: Path) -> tuple[dict, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%d_%H%M%S")
    txt_path = output_dir / f"GATE_BTC_MIGRATION_REPORT_{stamp}.txt"
    json_path = output_dir / f"GATE_BTC_MIGRATION_MANIFEST_{stamp}.json"
    zip_path = output_dir / f"GATE_BTC_MIGRATION_EVIDENCE_{stamp}.zip"
    errors: list[str] = []
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() != "true":
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        for forbidden in ("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY"):
            if os.environ.get(forbidden):
                raise RuntimeError(f"forbidden operational credential present: {forbidden}")
    except Exception:
        errors.append(traceback.format_exc())
    finished = datetime.now(timezone.utc)
    status = "PASS" if not errors else "ERROR"
    provenance = _provenance()
    manifest = {
        "schema": "gate-btc-migration-evidence-v1", "status": status,
        "stage_reached": "REMOTE_RUNNER_SAFETY_SMOKE",
        "started_at_utc": started.isoformat(), "finished_at_utc": finished.isoformat(),
        "git_commit": provenance["checked_out_commit"],
        "git_ref": provenance["checked_out_ref"],
        "source_head_sha": provenance["source_head_sha"],
        "source_head_ref": provenance["source_head_ref"],
        "provenance": provenance,
        "github_run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
        "network_actions": "NONE_BY_RUNNER", "locks": LOCKS, "errors": errors,
        "next_action": "COMPARE_WITH_LOCAL_REFERENCE" if status == "PASS" else "REPAIR_BEFORE_MIGRATION",
    }
    json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["GATE BTC — QRDS/QOS MIGRATION REPORT", f"STATUS={status}",
             "STAGE_REACHED=REMOTE_RUNNER_SAFETY_SMOKE",
             f"STARTED_AT_UTC={manifest['started_at_utc']}", f"FINISHED_AT_UTC={manifest['finished_at_utc']}",
             f"CHECKED_OUT_COMMIT={provenance['checked_out_commit']}",
             f"CHECKED_OUT_REF={provenance['checked_out_ref']}",
             f"SOURCE_HEAD_SHA={provenance['source_head_sha']}",
             f"SOURCE_HEAD_REF={provenance['source_head_ref']}",
             f"BASE_SHA={provenance['base_sha']}", f"BASE_REF={provenance['base_ref']}",
             f"GITHUB_EVENT_NAME={provenance['github_event_name']}",
             f"GITHUB_RUN_ID={manifest['github_run_id']}", "RESEARCH_ONLY=True",
             "ORDERS_ALLOWED=False", "ORDERS_GENERATED=0", "REAL_CAPITAL_USED=0",
             "PROMOTION_ALLOWED=False", "OPERATIONAL_STATUS=NOT_APPROVED",
             "NETWORK_ACTIONS=NONE_BY_RUNNER", f"NEXT_ACTION={manifest['next_action']}", "", "ERRORS:",
             *(errors or ["NONE"])]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    checksums = output_dir / f"SHA256SUMS_{stamp}.txt"
    checksums.write_text(f"{_sha256(txt_path)}  {txt_path.name}\n{_sha256(json_path)}  {json_path.name}\n", encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (txt_path, json_path, checksums):
            archive.write(path, path.name)
    return manifest, txt_path, json_path, zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/gate_btc_migration"))
    args = parser.parse_args()
    manifest, *_ = run(args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
