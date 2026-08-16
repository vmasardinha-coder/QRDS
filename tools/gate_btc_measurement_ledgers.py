#!/usr/bin/env python3
"""CLI for all prospective GATE BTC evidence measurements."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.gate_btc_lock_ledger import append_lock as _append_lock_strict, initialize_lock, initialize_source_anchor
from tools.gate_btc_measurement_common import load_json, safe_gateway
from tools.gate_btc_measurement_status import audit_d50, build_status


_PRICE_BLOCKER_PREFIXES = (
    "missing prior price for ",
    "missing current price for ",
    "stale prior price for ",
    "stale current price for ",
)
_GAP_BLOCKER_PREFIX = "LOCK requires consecutive close "


def append_lock(args) -> int:
    """Append LOCK evidence, failing closed but non-fatally on data blockers.

    Missing/stale required prices and a previously unresolved calendar-day gap are
    evidence-availability blockers, not permission to drop an asset, synthesize a
    return, or backfill a missed prospective close. The strict ledger writer raises
    before any snapshot mutation. This wrapper records an immutable diagnostic and
    returns 0 so independent Gateway/V2A evidence from the same Daily Research run
    can still be persisted. All other RuntimeError conditions remain fatal.
    """
    try:
        return _append_lock_strict(args)
    except RuntimeError as exc:
        message = str(exc)
        is_price_blocker = message.startswith(_PRICE_BLOCKER_PREFIXES)
        is_gap_blocker = message.startswith(_GAP_BLOCKER_PREFIX)
        if not (is_price_blocker or is_gap_blocker):
            raise

        diagnostics = args.ledger_dir / "diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        target = diagnostics / f"{args.snapshot_id}.json"
        if is_gap_blocker:
            status = "BLOCKED_UNRESOLVED_REQUIRED_PRIOR_CLOSE"
            blocker_type = "UNRESOLVED_PROSPECTIVE_GAP"
        else:
            status = "BLOCKED_MISSING_OR_STALE_REQUIRED_PRICE"
            blocker_type = "MISSING_OR_STALE_REQUIRED_PRICE"
        payload = {
            "schema": "gate_btc.lock25_50_blocked_snapshot.v1",
            "status": status,
            "blocker_type": blocker_type,
            "snapshot_id": args.snapshot_id,
            "cycle_id": args.cycle_id,
            "reason": message,
            "snapshot_appended": False,
            "mutation_performed": False,
            "asset_drop_allowed": False,
            "synthetic_return_allowed": False,
            "backfill_allowed": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders_generated": 0,
            "real_capital_used": 0,
        }
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing != rendered:
                # Preserve both immutable observations. Different exact source
                # artifacts can expose different blockers for the same close;
                # neither may overwrite the other or block independent ledgers.
                suffix = hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:12]
                alternate = diagnostics / f"{args.snapshot_id}.{suffix}.json"
                if alternate.exists() and alternate.read_text(encoding="utf-8") != rendered:
                    raise RuntimeError(f"LOCK blocker diagnostic hash conflict for {args.snapshot_id}")
                alternate.write_text(rendered, encoding="utf-8")
        else:
            target.write_text(rendered, encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    gateway = sub.add_parser("append-gateway-safe")
    gateway.add_argument("--manifest", type=Path, required=True)
    gateway.add_argument("--snapshot-status", type=Path, required=True)
    gateway.add_argument("--compositions", type=Path, required=True)
    gateway.add_argument("--execution-profiles", type=Path, required=True)
    gateway.add_argument("--snapshot-id", required=True)
    gateway.add_argument("--ledger-dir", type=Path, required=True)
    gateway.set_defaults(func=safe_gateway)

    init = sub.add_parser("initialize-lock")
    init.add_argument("--contract", type=Path, required=True)
    init.add_argument("--cycle-id", required=True)
    init.add_argument("--first-eligible-close", required=True)
    init.add_argument("--ledger-dir", type=Path, required=True)
    init.set_defaults(func=initialize_lock)

    source = sub.add_parser("initialize-lock-source")
    source.add_argument("--contract", type=Path, required=True)
    source.add_argument("--current-portfolios", type=Path, required=True)
    source.add_argument("--monthly-allocations", type=Path, required=True)
    source.add_argument("--equity-curves", type=Path, required=True)
    source.add_argument("--v2a-config", type=Path, required=True)
    source.add_argument("--base-date", required=True)
    source.add_argument("--cycle-id", required=True)
    source.add_argument("--ledger-dir", type=Path, required=True)
    source.set_defaults(func=initialize_source_anchor)

    lock = sub.add_parser("append-lock")
    lock.add_argument("--contract", type=Path, required=True)
    lock.add_argument("--master-daily", type=Path, required=True)
    lock.add_argument("--current-portfolios", type=Path, required=True)
    lock.add_argument("--snapshot-id", required=True)
    lock.add_argument("--cycle-id", required=True)
    lock.add_argument("--ledger-dir", type=Path, required=True)
    lock.set_defaults(func=append_lock)

    d50 = sub.add_parser("audit-d50-deep")
    d50.add_argument("--frozen-row", type=Path, required=True)
    d50.add_argument("--candidate-row", type=Path, required=True)
    d50.add_argument("--ignore-field", action="append")
    d50.add_argument("--output", type=Path, required=True)
    d50.set_defaults(func=audit_d50)

    status = sub.add_parser("build-status")
    status.add_argument("--delta-gate", type=Path, required=True)
    status.add_argument("--gateway-status", type=Path, required=True)
    status.add_argument("--lock-status", type=Path, required=True)
    status.add_argument("--d50-status", type=Path)
    status.add_argument("--output", type=Path, required=True)
    status.set_defaults(func=build_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
