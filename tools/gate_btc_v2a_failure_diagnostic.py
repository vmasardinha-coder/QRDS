#!/usr/bin/env python3
"""Advisory-only diagnosis for V2A public-data failures.

This tool classifies evidence gaps without changing the frozen V2A universe,
source order, denominator, strategy inputs, or any research methodology. It is
intended to distinguish simple history-length gaps from rows that deserve
semantic scope review and rows that are candidates for source-redundancy work.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


RWA_PATTERNS = (
    " fund", "fund ", "treasury", "t-bill", "t-bills", "tokenized",
    "reinsurance", "rent financing", "money market", "government securities",
    "institutional digital liquidity", "us dollar yield", "kinesis gold",
    "kinesis silver",
)
CASHLIKE_SYMBOL_PATTERNS = (
    re.compile(r"^USD[A-Z0-9]*$"),
    re.compile(r"^[A-Z0-9]*USD$"),
)
CASHLIKE_EXPLICIT = {"GHO", "USX", "A7A5", "CRVUSD"}
ONLY_ROWS = re.compile(r"only\s+(\d+)\s+rows", re.IGNORECASE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def semantic_flags(symbol: str, coin_id: str, name: str) -> list[str]:
    text = f" {coin_id} {name} ".lower()
    flags: list[str] = []
    if any(pattern in text for pattern in RWA_PATTERNS):
        flags.append("RWA_OR_TOKENIZED_NAME_PATTERN")
    if symbol in CASHLIKE_EXPLICIT or any(pattern.match(symbol) for pattern in CASHLIKE_SYMBOL_PATTERNS):
        flags.append("CASHLIKE_OR_STABLE_SYMBOL_PATTERN")
    return flags


def build_diagnostic(universe_rows: list[dict[str, str]], failure_rows: list[dict[str, str]], manifest: dict[str, Any]) -> dict[str, Any]:
    by_symbol = {str(row.get("symbol", "")).upper(): row for row in universe_rows}
    details: list[dict[str, Any]] = []
    counts = {
        "WAIT_FOR_HISTORY": 0,
        "SEMANTIC_SCOPE_REVIEW": 0,
        "SOURCE_RECOVERY_CANDIDATE": 0,
        "UNMAPPED_FAILURE": 0,
    }

    for failure in failure_rows:
        symbol = str(failure.get("symbol", "")).upper().strip()
        reason = str(failure.get("reason", "")).strip()
        source = by_symbol.get(symbol)
        if source is None:
            action_class = "UNMAPPED_FAILURE"
            flags = ["SYMBOL_NOT_FOUND_IN_CURRENT_UNIVERSE"]
            history_rows = None
            coin_id = ""
            name = ""
            rank = None
        else:
            coin_id = str(source.get("id", ""))
            name = str(source.get("name", ""))
            rank_raw = source.get("market_cap_rank", "")
            try:
                rank = int(float(rank_raw)) if str(rank_raw).strip() else None
            except ValueError:
                rank = None
            match = ONLY_ROWS.search(reason)
            history_rows = int(match.group(1)) if match else None
            flags = semantic_flags(symbol, coin_id, name)
            if history_rows is not None and history_rows < 200:
                action_class = "WAIT_FOR_HISTORY"
            elif flags:
                action_class = "SEMANTIC_SCOPE_REVIEW"
            else:
                action_class = "SOURCE_RECOVERY_CANDIDATE"

        counts[action_class] += 1
        details.append({
            "symbol": symbol,
            "coin_id": coin_id,
            "name": name,
            "market_cap_rank": rank,
            "failure_reason": reason,
            "observed_history_rows": history_rows,
            "semantic_flags": flags,
            "action_class": action_class,
        })

    attempted = int(manifest.get("attempted_symbols", 0))
    loaded = int(manifest.get("loaded_symbols", 0))
    failed = int(manifest.get("failed_symbols", len(failure_rows)))
    if failed != len(failure_rows):
        raise RuntimeError(f"failure row count differs from manifest: {len(failure_rows)} != {failed}")
    if attempted != loaded + failed:
        raise RuntimeError(f"attempted != loaded + failed: {attempted} != {loaded} + {failed}")

    return {
        "schema": "gate_btc.v2a_failure_diagnostic.v1",
        "status": "PASS_ADVISORY_DIAGNOSTIC",
        "data_as_of": manifest.get("data_as_of"),
        "attempted_symbols": attempted,
        "loaded_symbols": loaded,
        "failed_symbols": failed,
        "coverage_pct": (100.0 * loaded / attempted) if attempted else 0.0,
        "action_counts": counts,
        "rows": details,
        "interpretation": {
            "WAIT_FOR_HISTORY": "Observed source returned fewer than 200 rows; no methodology action implied.",
            "SEMANTIC_SCOPE_REVIEW": "Name/symbol has a conservative RWA/tokenized/cash-like flag; review only, no automatic exclusion.",
            "SOURCE_RECOVERY_CANDIDATE": "No conservative semantic flag and no explicit short-history result; candidate for independent source-redundancy investigation only.",
            "UNMAPPED_FAILURE": "Failure symbol was not found in the same point-in-time universe and must be investigated fail-closed.",
        },
        "advisory_only": True,
        "denominator_changed": False,
        "universe_changed": False,
        "source_order_changed": False,
        "source_substitution_performed": False,
        "feeds_frozen_engine": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--failures-csv", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    if not args.source_run_id.isdigit():
        raise RuntimeError("source_run_id must be numeric")

    manifest = load_json(args.manifest)
    diagnostic = build_diagnostic(read_csv(args.universe_csv), read_csv(args.failures_csv), manifest)
    expected_snapshot = f"{manifest.get('data_as_of')}-run-{args.source_run_id}"
    if args.snapshot_id != expected_snapshot:
        raise RuntimeError(f"snapshot_id must equal {expected_snapshot}")
    diagnostic.update({
        "snapshot_id": args.snapshot_id,
        "source_run_id": args.source_run_id,
        "source_manifest_sha256": sha256(args.manifest),
        "source_universe_sha256": sha256(args.universe_csv),
        "source_failures_sha256": sha256(args.failures_csv),
    })
    atomic_json(args.output, diagnostic)
    print(json.dumps({
        "status": diagnostic["status"],
        "snapshot_id": args.snapshot_id,
        "failed_symbols": diagnostic["failed_symbols"],
        "action_counts": diagnostic["action_counts"],
        "feeds_frozen_engine": False,
        "methodology_changes": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
