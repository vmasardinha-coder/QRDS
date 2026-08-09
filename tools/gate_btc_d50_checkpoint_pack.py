#!/usr/bin/env python3
"""Build an immutable D50 checkpoint pack for mirror reconciliation.

The pack builder reads the live local D50 state plus the most recent successful
source-revision repair evidence, resolves the published GitHub D50 status mirror,
runs the fail-closed reconciliation audit, and produces one ZIP containing the
exact evidence bytes and SHA-256 manifest.

It never writes to GitHub, never mutates the D50 ledger/status, never changes a
strategy, and never creates orders or uses capital.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Support both `python -m tools...` and direct `python tools/...py` execution.
try:
    from tools.gate_btc_d50_mirror_reconcile import (
        ReconciliationError,
        build_audit,
        sha256_file,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised by the CLI smoke test
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.gate_btc_d50_mirror_reconcile import (
        ReconciliationError,
        build_audit,
        sha256_file,
    )


class CheckpointPackError(RuntimeError):
    """Fail-closed checkpoint-pack error."""


RESULT_NAMES = ("RESULTADO_FINAL.txt", "RESULTADO_CONSOLIDACAO.txt")
REPAIR_PREFIXES = ("D50_SOURCE_HASH_REPAIR_", "FINAL_CONSOLIDATION_")


def parse_key_value_text(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def successful_repair_result(path: Path) -> bool:
    try:
        values = parse_key_value_text(path)
    except OSError:
        return False
    return (
        values.get("STATUS", "").startswith("PASS")
        and values.get("FROZEN_ROWS_PRESERVED", "").lower() == "true"
        and values.get("RESEARCH_ONLY", "").lower() == "true"
        and values.get("OPERATIONAL_STATUS") == "NOT_APPROVED"
        and values.get("ORDERS") == "0"
        and values.get("CAPITAL") == "0"
    )


def find_diagnostics_dir(root: Path) -> Path | None:
    direct = root / "SOURCE_REVISION_DIAGNOSTICS"
    if direct.is_dir() and any(direct.glob("*.json")):
        return direct
    matches = [
        path
        for path in root.rglob("SOURCE_REVISION_DIAGNOSTICS")
        if path.is_dir() and any(path.glob("*.json"))
    ]
    if matches:
        return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]
    return None


def find_repair_evidence(base: Path) -> dict[str, Path]:
    evidence_root = base / "evidence"
    if not evidence_root.is_dir():
        raise CheckpointPackError(f"D50 evidence directory not found: {evidence_root}")

    candidates = [
        path
        for path in evidence_root.iterdir()
        if path.is_dir() and path.name.startswith(REPAIR_PREFIXES)
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    rejection_reasons: list[str] = []
    for root in candidates:
        result = next((root / name for name in RESULT_NAMES if (root / name).is_file()), None)
        prior = root / "BACKUP" / "d50_prospective_observations_v2.csv"
        diagnostics = find_diagnostics_dir(root)
        if result is None:
            rejection_reasons.append(f"{root.name}: result file missing")
            continue
        if not successful_repair_result(result):
            rejection_reasons.append(f"{root.name}: result is not a complete PASS")
            continue
        if not prior.is_file():
            rejection_reasons.append(f"{root.name}: prior frozen ledger missing")
            continue
        if diagnostics is None:
            rejection_reasons.append(f"{root.name}: source-revision diagnostics missing")
            continue
        return {
            "root": root,
            "result": result,
            "prior_ledger": prior,
            "diagnostics": diagnostics,
        }

    detail = "; ".join(rejection_reasons[:8]) or "no repair evidence candidates found"
    raise CheckpointPackError(f"no complete successful D50 repair evidence found: {detail}")


def discover_repo(explicit: Path | None) -> Path:
    if explicit is not None:
        candidate = explicit.resolve()
        if not (candidate / ".git").exists():
            raise CheckpointPackError(f"not a Git repository: {candidate}")
        return candidate

    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists():
        return cwd

    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        desktop_candidate = Path(userprofile) / "Desktop" / "Projetos" / "QRDS"
        if (desktop_candidate / ".git").exists():
            return desktop_candidate.resolve()

    raise CheckpointPackError("canonical QRDS Git repository not found; pass --repo")


def resolve_remote_status(repo: Path, explicit: Path | None, destination: Path) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise CheckpointPackError(f"remote status file not found: {explicit}")
        shutil.copy2(explicit, destination)
        return destination

    try:
        subprocess.run(
            ["git", "-C", str(repo), "fetch", "origin", "gate-btc-runtime", "--quiet"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "show",
                "origin/gate-btc-runtime:runtime/ledgers/d50/STATUS.json",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise CheckpointPackError("could not resolve gate-btc-runtime D50 STATUS.json") from exc

    destination.write_text(result.stdout, encoding="utf-8")
    return destination


def copy_diagnostics(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    files = sorted(source.glob("*.json"))
    if not files:
        raise CheckpointPackError("source-revision diagnostics directory is empty")
    for path in files:
        shutil.copy2(path, destination / path.name)


def manifest_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "MANIFEST.json":
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def build_checkpoint_pack(
    *,
    base: Path,
    repo: Path | None,
    output_dir: Path,
    remote_status_path: Path | None = None,
    timestamp: datetime | None = None,
) -> Path:
    base = base.resolve()
    state = base / "state"
    local_status = state / "D50_PROSPECTIVE_STATUS_V2.json"
    local_ledger = state / "d50_prospective_observations_v2.csv"
    if not local_status.is_file() or not local_ledger.is_file():
        raise CheckpointPackError("current D50 state files are missing")

    repair = find_repair_evidence(base)
    canonical_repo = discover_repo(repo) if remote_status_path is None else (repo.resolve() if repo else Path.cwd())

    now = timestamp or datetime.now(timezone.utc)
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    final_zip = output_dir / f"GATE_BTC_D50_CHECKPOINT_PACK_{stamp}.zip"

    with tempfile.TemporaryDirectory(prefix="gate_btc_d50_checkpoint_") as temp_name:
        staging = Path(temp_name) / "GATE_BTC_D50_CHECKPOINT_PACK"
        current_dir = staging / "current"
        repair_dir = staging / "repair"
        remote_dir = staging / "remote"
        audit_dir = staging / "audit"
        current_dir.mkdir(parents=True)
        repair_dir.mkdir(parents=True)
        remote_dir.mkdir(parents=True)
        audit_dir.mkdir(parents=True)

        staged_status = current_dir / local_status.name
        staged_ledger = current_dir / local_ledger.name
        staged_prior = repair_dir / "prior_d50_prospective_observations_v2.csv"
        staged_result = repair_dir / "RESULTADO_REPARO.txt"
        staged_diagnostics = repair_dir / "SOURCE_REVISION_DIAGNOSTICS"
        staged_remote = remote_dir / "STATUS.json"
        staged_audit = audit_dir / "D50_MIRROR_RECONCILIATION_AUDIT.json"

        shutil.copy2(local_status, staged_status)
        shutil.copy2(local_ledger, staged_ledger)
        shutil.copy2(repair["prior_ledger"], staged_prior)
        shutil.copy2(repair["result"], staged_result)
        copy_diagnostics(repair["diagnostics"], staged_diagnostics)
        resolve_remote_status(canonical_repo, remote_status_path, staged_remote)

        audit = build_audit(
            local_status_path=staged_status,
            local_ledger_path=staged_ledger,
            remote_status_path=staged_remote,
            prior_ledger_path=staged_prior,
            diagnostics_dir=staged_diagnostics,
            repair_result_path=staged_result,
        )
        if not str(audit.get("status", "")).startswith("PASS_MIRROR_"):
            raise CheckpointPackError(f"reconciliation did not pass: {audit.get('status')}")
        if audit.get("runtime_mutation_performed") is not False:
            raise CheckpointPackError("reconciliation unexpectedly reports runtime mutation")
        if audit.get("orders_generated") != 0 or audit.get("real_capital_used") != 0:
            raise CheckpointPackError("reconciliation safety invariant changed")
        staged_audit.write_text(
            json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        readme = staging / "README.txt"
        readme.write_text(
            "GATE BTC D50 CHECKPOINT PACK\n"
            "Purpose: evidence-only mirror reconciliation.\n"
            "This package is NOT an operational authorization.\n"
            "It performs no GitHub runtime mutation, no order generation and no capital use.\n"
            "A PASS audit is only a candidate for a separately reviewed status-mirror update.\n",
            encoding="utf-8",
        )

        manifest = {
            "schema": "gate_btc.d50_checkpoint_pack.v1",
            "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
            "repair_evidence_id": repair["root"].name,
            "audit_status": audit["status"],
            "candidate_only": True,
            "runtime_mutation_performed": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders_generated": 0,
            "real_capital_used": 0,
            "files": manifest_entries(staging),
        }
        (staging / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        if final_zip.exists():
            final_zip.unlink()
        with zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(staging.parent).as_posix())

    return final_zip


def default_base() -> Path:
    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        raise CheckpointPackError("LOCALAPPDATA is unavailable; pass --base")
    return Path(localappdata) / "GATE_BTC_D50_AUTOPILOT_V2"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--remote-status", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        base = args.base or default_base()
        output_dir = args.output_dir or (base / "evidence" / "CHECKPOINT_PACKS")
        pack = build_checkpoint_pack(
            base=base,
            repo=args.repo,
            output_dir=output_dir,
            remote_status_path=args.remote_status,
        )
    except (CheckpointPackError, ReconciliationError) as exc:
        print(f"D50_CHECKPOINT_PACK=FAIL_CLOSED: {exc}")
        return 2

    print("D50_CHECKPOINT_PACK=PASS")
    print(f"PACK={pack}")
    print("RUNTIME_MUTATION=0")
    print("ORDERS=0")
    print("CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
