#!/usr/bin/env python3
"""CLI for all prospective GATE BTC evidence measurements."""
from __future__ import annotations

import argparse
from pathlib import Path

from tools.gate_btc_lock_ledger import append_lock, initialize_lock, initialize_source_anchor
from tools.gate_btc_measurement_common import load_json, safe_gateway
from tools.gate_btc_measurement_status import audit_d50, build_status


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
