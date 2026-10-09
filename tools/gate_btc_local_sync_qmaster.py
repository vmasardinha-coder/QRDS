#!/usr/bin/env python3
"""Safely fast-forward two local QRDS clones and audit QMASTER provenance.

Never resets, rebases, stashes, or deletes local work. Emits full sanitized Git
errors so a failed sync cannot silently look like a fresh local observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def redact(s: str) -> str:
    s = re.sub(r"(https?://)[^\s/@]+@", r"\1[REDACTED]@", s)
    return re.sub(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+", "[REDACTED]", s)


def git(root: Path, *args: str, binary: bool = False):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)} rc={p.returncode}: "
                           + redact(p.stderr.decode("utf-8", errors="replace")))
    return p.stdout if binary else p.stdout.decode("utf-8", errors="replace").strip()


def sync(root: Path, branch: str, apply_ff: bool) -> dict:
    out = {"root": str(root), "branch": branch, "status": "FAIL"}
    try:
        actual = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        if actual != branch:
            raise RuntimeError(f"expected checked-out branch {branch}; got {actual}")
        out["head_before"] = git(root, "rev-parse", "HEAD")
        out["dirty"] = bool(git(root, "status", "--porcelain"))
        git(root, "fetch", "--no-tags", "origin", branch)
        out["remote_head"] = git(root, "rev-parse", "FETCH_HEAD")
        if out["head_before"] == out["remote_head"]:
            out["status"] = "CURRENT"
        else:
            p = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                                "HEAD", "FETCH_HEAD"], capture_output=True)
            if p.returncode == 1:
                out["status"] = "DIVERGED_REVIEW_REQUIRED"
            elif p.returncode:
                raise RuntimeError(redact(p.stderr.decode("utf-8", errors="replace")))
            elif out["dirty"]:
                out["status"] = "FAST_FORWARD_BLOCKED_DIRTY"
            elif apply_ff:
                git(root, "merge", "--ff-only", "FETCH_HEAD")
                out["status"] = "FAST_FORWARDED"
            else:
                out["status"] = "FAST_FORWARD_AVAILABLE"
        out["head_after"] = git(root, "rev-parse", "HEAD")
    except Exception as exc:
        out["error"] = redact(str(exc))
    return out


def qmaster(runtime: Path, expected_date: str | None) -> dict:
    rel = Path("runtime/GATE_BTC_QMASTER_LATEST")
    out = {"status": "FAIL"}
    try:
        sidecar_path = runtime / f"{rel}.txt"
        csv_path = runtime / f"{rel}.csv"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        remote_sidecar = json.loads(git(runtime, "show", "FETCH_HEAD:runtime/GATE_BTC_QMASTER_LATEST.txt"))
        remote_digest = hashlib.sha256(git(runtime, "show", "FETCH_HEAD:runtime/GATE_BTC_QMASTER_LATEST.csv", binary=True)).hexdigest()
        out.update({"local_date": sidecar.get("data_as_of"), "remote_date": remote_sidecar.get("data_as_of"),
                    "local_csv_sha256": digest, "remote_csv_sha256": remote_digest,
                    "rows": sidecar.get("rows"), "symbols": sidecar.get("symbols")})
        if (sidecar.get("status") != "PASS" or remote_sidecar.get("status") != "PASS"
                or sidecar.get("research_only") is not True
                or sidecar.get("orders_generated") != 0
                or sidecar.get("real_capital_used") != 0
                or digest != sidecar.get("csv_sha256")
                or remote_digest != remote_sidecar.get("csv_sha256")):
            raise ValueError("QMASTER status, safety, or sidecar hash mismatch")
        if expected_date and remote_sidecar.get("data_as_of") != expected_date:
            raise ValueError(f"remote QMASTER date differs from expected {expected_date}")
        out["status"] = ("MATCH_REMOTE" if digest == remote_digest
                         and sidecar.get("data_as_of") == remote_sidecar.get("data_as_of")
                         else "STALE_LOCAL")
    except Exception as exc:
        out["error"] = redact(str(exc))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-root", type=Path, required=True)
    ap.add_argument("--runtime-root", type=Path, required=True)
    ap.add_argument("--expected-date")
    ap.add_argument("--apply-ff", action="store_true")
    ap.add_argument("--output", type=Path, default=Path("local_sync_qmaster_audit.json"))
    args = ap.parse_args()
    main_row = sync(args.main_root, "main", args.apply_ff)
    runtime_row = sync(args.runtime_root, "gate-btc-runtime", args.apply_ff)
    qm = qmaster(args.runtime_root, args.expected_date) if runtime_row.get("remote_head") else {"status": "BLOCKED_BY_SYNC"}
    result = {"schema": "gate_btc.local_sync_qmaster_audit.v1",
              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "main": main_row, "runtime": runtime_row, "qmaster": qm,
              "orders": 0, "real_capital": 0, "research_only": True}
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if (main_row["status"] in ("CURRENT", "FAST_FORWARDED")
                 and runtime_row["status"] in ("CURRENT", "FAST_FORWARDED")
                 and qm["status"] == "MATCH_REMOTE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
