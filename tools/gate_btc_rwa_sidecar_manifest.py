#!/usr/bin/env python3
"""Build a point-in-time sidecar manifest for RWA/tokenized/cash-like review rows.

This manifest is observation-only. It consumes the advisory V2A failure
diagnostic and copies only rows already flagged for semantic scope review. It
never excludes them from V2A, never creates a tradable universe, and never
feeds any frozen strategy or report metric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def build(diagnostic: dict) -> dict:
    require(diagnostic.get("schema") == "gate_btc.v2a_failure_diagnostic.v1", "unexpected diagnostic schema")
    require(diagnostic.get("advisory_only") is True, "diagnostic must remain advisory-only")
    require(diagnostic.get("feeds_frozen_engine") is False, "diagnostic engine-feed boundary changed")
    require(diagnostic.get("source_substitution_performed") is False, "diagnostic source-substitution boundary changed")
    require(diagnostic.get("denominator_changed") is False, "diagnostic denominator boundary changed")
    require(diagnostic.get("universe_changed") is False, "diagnostic universe boundary changed")
    require(int(diagnostic.get("methodology_changes", 0)) == 0, "diagnostic methodology changed")

    rows = []
    for source in diagnostic.get("rows", []):
        if source.get("action_class") != "SEMANTIC_SCOPE_REVIEW":
            continue
        flags = sorted({str(flag) for flag in source.get("semantic_flags", []) if str(flag)})
        if not flags:
            raise RuntimeError(f"semantic review row without flags: {source.get('symbol')}")
        rows.append({
            "symbol": str(source.get("symbol", "")).upper(),
            "coin_id": str(source.get("coin_id", "")),
            "name": str(source.get("name", "")),
            "market_cap_rank": source.get("market_cap_rank"),
            "semantic_flags": flags,
            "failure_reason": str(source.get("failure_reason", "")),
            "observation_role": "SEPARATE_SCOPE_REVIEW_ONLY",
            "automatic_exclusion_from_v2a": False,
            "tradable_universe_member": False,
        })
    rows.sort(key=lambda item: (item["market_cap_rank"] is None, item["market_cap_rank"] or 10**9, item["symbol"]))
    rwa = sum("RWA_OR_TOKENIZED_NAME_PATTERN" in row["semantic_flags"] for row in rows)
    cashlike = sum("CASHLIKE_OR_STABLE_SYMBOL_PATTERN" in row["semantic_flags"] for row in rows)

    return {
        "schema": "gate_btc.rwa_tokenized_sidecar_manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_OBSERVATION_SIDECAR_ONLY",
        "data_as_of": diagnostic.get("data_as_of"),
        "source_snapshot_id": diagnostic.get("snapshot_id"),
        "candidate_count": len(rows),
        "rwa_or_tokenized_flag_count": rwa,
        "cashlike_or_stable_flag_count": cashlike,
        "rows": rows,
        "scope_statement": "Sidecar candidate manifest only. It does not declare that every flagged asset is an RWA, security, stablecoin or stock token; flags are conservative review heuristics from the existing diagnostic.",
        "stock_bases_adapter_implemented": False,
        "rwa_strategy_universe_created": False,
        "automatic_exclusion_from_v2a": False,
        "role": "SEPARATE_SCOPE_REVIEW_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "denominator_changed": False,
        "universe_changed": False,
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
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"}, "research-only must remain true")
    raw = args.diagnostic.read_bytes()
    diagnostic = json.loads(raw.decode("utf-8-sig"))
    payload = build(diagnostic)
    payload["source_diagnostic_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, args.output)
    print(json.dumps({
        "status": payload["status"],
        "candidate_count": payload["candidate_count"],
        "rwa_or_tokenized_flag_count": payload["rwa_or_tokenized_flag_count"],
        "cashlike_or_stable_flag_count": payload["cashlike_or_stable_flag_count"],
        "automatic_exclusion_from_v2a": False,
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
