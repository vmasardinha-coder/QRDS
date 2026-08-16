#!/usr/bin/env python3
"""Archive an interrupted LOCK series and create an explicitly authorized one.

This is the only supported reset path.  It preserves the original bytes under
``interrupted_series/``, records the dates that must never be retro-filled, and
then builds a fresh source anchor from the last close known before the new
prospective window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from argparse import Namespace
from datetime import timedelta
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_lock_ledger import initialize_lock, initialize_source_anchor
    from tools.gate_btc_measurement_common import (
        atomic_json, canonical_sha, file_sha, iso_day, load_json, require,
    )
except ModuleNotFoundError:  # direct ``python tools/...py`` execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.gate_btc_lock_ledger import initialize_lock, initialize_source_anchor
    from tools.gate_btc_measurement_common import (
        atomic_json, canonical_sha, file_sha, iso_day, load_json, require,
    )


ACTIVE_NAMES = ("ANCHOR.json", "SOURCE_ANCHOR.json", "STATUS.json", "snapshots", "diagnostics")


def _tree_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result[path.relative_to(root).as_posix()] = file_sha(path)
    return result


def _active_hashes(ledger_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in ACTIVE_NAMES:
        path = ledger_dir / name
        if path.is_file():
            result[name] = file_sha(path)
        elif path.is_dir():
            result.update({f"{name}/{key}": value for key, value in _tree_hashes(path).items()})
    return result


def _copy_active(ledger_dir: Path, archive: Path) -> None:
    archive.mkdir(parents=True, exist_ok=True)
    for name in ACTIVE_NAMES:
        source = ledger_dir / name
        if not source.exists():
            continue
        target = archive / name
        if source.is_dir():
            if target.exists():
                require(_tree_hashes(source) == _tree_hashes(target), f"archive differs for {name}")
            else:
                shutil.copytree(source, target, copy_function=shutil.copy2)
        elif target.exists():
            require(file_sha(source) == file_sha(target), f"archive differs for {name}")
        else:
            shutil.copy2(source, target)


def _remove_active(ledger_dir: Path) -> None:
    for name in ACTIVE_NAMES:
        path = ledger_dir / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def _validate_old_series(
    ledger_dir: Path,
    old_cycle_id: str,
    preserved_dates: list[str],
    excluded_dates: list[str],
) -> dict[str, Any]:
    anchor = load_json(ledger_dir / "ANCHOR.json")
    source = load_json(ledger_dir / "SOURCE_ANCHOR.json")
    require(anchor.get("cycle_id") == old_cycle_id, "active LOCK cycle does not match interrupted cycle")
    require(anchor.get("anchor_sha256") == canonical_sha(anchor, "anchor_sha256"), "invalid interrupted anchor")
    require(source.get("source_anchor_sha256") == canonical_sha(source, "source_anchor_sha256"), "invalid interrupted source anchor")
    actual = sorted(path.stem for path in (ledger_dir / "snapshots").glob("*.json"))
    require(actual == preserved_dates, f"interrupted snapshots differ: expected={preserved_dates} got={actual}")
    diagnostics = ledger_dir / "diagnostics"
    missing = [day for day in excluded_dates if not list(diagnostics.glob(f"{day}*.json"))]
    require(not missing, f"missing interruption diagnostics for dates={missing}")
    for path in (ledger_dir / "snapshots").glob("*.json"):
        payload = load_json(path)
        require(payload.get("snapshot_sha256") == canonical_sha(payload, "snapshot_sha256"), f"invalid snapshot hash {path.name}")
    return {
        "anchor_sha256": anchor["anchor_sha256"],
        "source_anchor_sha256": source["source_anchor_sha256"],
        "latest_snapshot_sha256": load_json(ledger_dir / "snapshots" / f"{preserved_dates[-1]}.json")["snapshot_sha256"],
    }


def reanchor(args: argparse.Namespace) -> dict[str, Any]:
    base_date = iso_day(args.base_date, "base date")
    first_close = iso_day(args.first_eligible_close, "first eligible close")
    require(base_date + timedelta(days=1) == first_close, "new first eligible close must immediately follow base date")
    preserved = sorted(args.preserved_date)
    excluded = sorted(args.excluded_date)
    require(preserved, "preserved interrupted dates are required")
    require(excluded, "explicit retroactive-fill exclusions are required")
    require(len(set(preserved)) == len(preserved), "duplicate preserved dates are not allowed")
    require(len(set(excluded)) == len(excluded), "duplicate excluded dates are not allowed")
    preserved_days = [iso_day(day, "preserved date") for day in preserved]
    excluded_days = [iso_day(day, "excluded date") for day in excluded]
    require(max(preserved) < min(excluded), "excluded gap must follow preserved series")
    require(max(excluded) == args.base_date, "excluded gap must end on the new base date")
    expected_preserved = []
    cursor = preserved_days[0]
    while cursor <= preserved_days[-1]:
        expected_preserved.append(cursor.isoformat())
        cursor += timedelta(days=1)
    require(preserved == expected_preserved, "preserved interrupted series must be consecutive")
    expected_excluded = []
    cursor = preserved_days[-1] + timedelta(days=1)
    while cursor <= base_date:
        expected_excluded.append(cursor.isoformat())
        cursor += timedelta(days=1)
    require(excluded == expected_excluded, "every interrupted gap date must prohibit retroactive fill")

    ledger_dir = args.ledger_dir
    archive = ledger_dir / "interrupted_series" / args.old_cycle_id
    active_anchor = ledger_dir / "ANCHOR.json"
    old_hashes: dict[str, Any]
    if active_anchor.exists() and load_json(active_anchor).get("cycle_id") == args.old_cycle_id:
        old_hashes = _validate_old_series(
            ledger_dir,
            args.old_cycle_id,
            preserved,
            excluded,
        )
        active_hashes = _active_hashes(ledger_dir)
        _copy_active(ledger_dir, archive)
        require(active_hashes == _tree_hashes(archive), "interrupted archive verification failed")
        _remove_active(ledger_dir)
    else:
        require((archive / "ANCHOR.json").exists(), "interrupted series archive is unavailable")
        archived_anchor = load_json(archive / "ANCHOR.json")
        require(archived_anchor.get("cycle_id") == args.old_cycle_id, "archived cycle mismatch")
        archived_source = load_json(archive / "SOURCE_ANCHOR.json")
        archived_latest = load_json(archive / "snapshots" / f"{preserved[-1]}.json")
        old_hashes = {
            "anchor_sha256": archived_anchor["anchor_sha256"],
            "source_anchor_sha256": archived_source["source_anchor_sha256"],
            "latest_snapshot_sha256": archived_latest["snapshot_sha256"],
        }

    interruption = {
        "schema": "gate_btc.lock25_50_interrupted_series.v1",
        "status": "INTERRUPTED_PRESERVED_NO_RETROACTIVE_FILL",
        "cycle_id": args.old_cycle_id,
        "preserved_snapshot_dates": preserved,
        "preserved_snapshot_count": len(preserved),
        "interrupted_gap_dates": excluded,
        "retroactive_fill_allowed": False,
        "interruption_reason": args.interruption_reason,
        "reanchor_authorized_at_utc": args.authorized_at_utc,
        "authorization_text_sha256": hashlib.sha256(args.authorization_text.encode("utf-8")).hexdigest(),
        **old_hashes,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    interruption["interruption_sha256"] = canonical_sha(interruption, "interruption_sha256")
    interruption_path = archive / "INTERRUPTION.json"
    if interruption_path.exists():
        require(load_json(interruption_path) == interruption, "interruption authorization record differs")
    else:
        atomic_json(interruption_path, interruption)

    history = {
        "schema": "gate_btc.lock25_50_series_history.v1",
        "active_cycle_id": args.new_cycle_id,
        "reanchor_authorized_at_utc": args.authorized_at_utc,
        "retroactive_fill_prohibited_dates": excluded,
        "interrupted_series": [{
            "cycle_id": args.old_cycle_id,
            "path": f"interrupted_series/{args.old_cycle_id}",
            "interruption_sha256": interruption["interruption_sha256"],
            "preserved_snapshot_dates": preserved,
        }],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    history["series_history_sha256"] = canonical_sha(history, "series_history_sha256")
    history_path = ledger_dir / "SERIES_HISTORY.json"
    if history_path.exists():
        require(load_json(history_path) == history, "LOCK series history differs")
    else:
        atomic_json(history_path, history)

    initialize_lock(Namespace(
        contract=args.contract,
        cycle_id=args.new_cycle_id,
        first_eligible_close=args.first_eligible_close,
        ledger_dir=ledger_dir,
    ))
    initialize_source_anchor(Namespace(
        contract=args.contract,
        current_portfolios=args.current_portfolios,
        monthly_allocations=args.monthly_allocations,
        equity_curves=args.equity_curves,
        v2a_config=args.v2a_config,
        base_date=args.base_date,
        cycle_id=args.new_cycle_id,
        ledger_dir=ledger_dir,
        source_run_id=args.source_run_id,
        source_artifact_sha256=args.source_artifact_sha256,
    ))
    status = load_json(ledger_dir / "STATUS.json")
    require(status.get("cycle_id") == args.new_cycle_id, "new LOCK cycle was not activated")
    require(status.get("valid_snapshot_count") == 0, "new LOCK cycle must begin at zero")
    return {
        "status": "REANCHORED_WAITING_FIRST_UNTOUCHED_CLOSE",
        "old_cycle_id": args.old_cycle_id,
        "new_cycle_id": args.new_cycle_id,
        "first_eligible_close": args.first_eligible_close,
        "preserved_snapshot_dates": preserved,
        "retroactive_fill_prohibited_dates": excluded,
        "interruption_sha256": interruption["interruption_sha256"],
        "series_history_sha256": history["series_history_sha256"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--old-cycle-id", required=True)
    parser.add_argument("--new-cycle-id", required=True)
    parser.add_argument("--base-date", required=True)
    parser.add_argument("--first-eligible-close", required=True)
    parser.add_argument("--preserved-date", action="append", required=True)
    parser.add_argument("--excluded-date", action="append", required=True)
    parser.add_argument("--authorized-at-utc", required=True)
    parser.add_argument("--authorization-text", required=True)
    parser.add_argument("--interruption-reason", required=True)
    parser.add_argument("--current-portfolios", type=Path, required=True)
    parser.add_argument("--monthly-allocations", type=Path, required=True)
    parser.add_argument("--equity-curves", type=Path, required=True)
    parser.add_argument("--v2a-config", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-artifact-sha256", required=True)
    args = parser.parse_args()
    result = reanchor(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
