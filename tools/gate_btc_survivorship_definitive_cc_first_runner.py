#!/usr/bin/env python3
"""Stage direct-USD recovery before the expensive Bybit archive layer.

Research-only wrapper. The definitive runner already contains both recovery
adapters. This staging wrapper intentionally defers the trade-level Bybit
archive so the cheap CryptoCompare CCCAGG direct-USD layer can be measured
independently first. No strategy, factor, weight, execution, or engine setting
is changed. Bybit remains available for a later residual-only pass.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import gate_btc_survivorship_definitive_runner as runner

COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]
_ORIGINAL_WRITE = runner._write_text_cascade


def _defer_bybit_archive(session, identity, symbols, outdir: Path):
    unique = sorted(set(str(s) for s in symbols))
    empty = pd.DataFrame(columns=COLS)
    coverage = pd.DataFrame([
        {
            "symbol": symbol,
            "status": "DEFERRED_CC_DIRECT_FIRST",
            "rows": 0,
            "first_date": None,
            "last_date": None,
            "archive_months_pass": 0,
            "archive_bytes": 0,
        }
        for symbol in unique
    ])
    pd.DataFrame(columns=[
        "symbol", "pair", "month", "url", "sha256", "compressed_bytes",
        "status", "error", "daily_rows", "index_url",
    ]).to_csv(outdir / "BYBIT_ARCHIVE_MANIFEST.csv", index=False)
    empty.to_csv(outdir / "BYBIT_ARCHIVE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    coverage.to_csv(outdir / "BYBIT_ARCHIVE_COVERAGE.csv", index=False)
    policy = {
        "schema": "gate_btc.bybit_archive_stage_policy.v1",
        "status": "DEFERRED_CC_DIRECT_FIRST",
        "candidate_symbols": len(unique),
        "reason": "measure cheap direct-USD recovery before trade-level monthly archive downloads",
        "bybit_adapter_removed": False,
        "future_residual_only_pass_allowed": True,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    (outdir / "BYBIT_ARCHIVE_STAGE_POLICY.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"BYBIT_PUBLIC_ARCHIVE_STAGE=DEFERRED candidates={len(unique)}", flush=True)
    return empty, coverage


def _write_staged_text(outdir, manifest, alpha, survivor_alpha, identity, coverage):
    _ORIGINAL_WRITE(outdir, manifest, alpha, survivor_alpha, identity, coverage)
    method = outdir / "METODOLOGIA.md"
    if method.is_file():
        with method.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## Staged recovery note\n\n"
                "For this run only, the Bybit public trade-archive adapter was deliberately deferred so CryptoCompare CCCAGG direct USD (`tryConversion=false`) could be measured independently before any expensive trade-level monthly downloads. The Bybit adapter remains in the research branch and may be run later only against the residual unresolved set.\n"
            )
    executive = outdir / "EXECUTIVE_SUMMARY.txt"
    if executive.is_file():
        with executive.open("a", encoding="utf-8") as handle:
            handle.write("BYBIT_ARCHIVE_STAGE=DEFERRED_CC_DIRECT_FIRST\n")


def main() -> int:
    runner.bybit_archive.collect = _defer_bybit_archive
    runner._write_text_cascade = _write_staged_text
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
