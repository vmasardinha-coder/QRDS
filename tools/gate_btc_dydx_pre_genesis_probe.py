#!/usr/bin/env python3
"""Pre-genesis ethDYDX evidence probe for GATE BTC.

Research-only helper. The dYdX Chain genesis boundary is fixed at
2023-10-26. Direct exchange DYDX spot history strictly before that date is
therefore evidence for the original Ethereum token only. This tool never
stitches the Ethereum token to native dYdX Chain DYDX and never feeds the
frozen engine.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import requests

import gate_btc_exchange_pit_history as exchange

CHAIN_GENESIS = pd.Timestamp("2023-10-26")
CMC_FIRST_SNAPSHOT = pd.Timestamp("2021-09-30")
CMC_LAST_PRE_GENESIS_SNAPSHOT = pd.Timestamp("2023-09-30")
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def bound_pre_genesis(history: pd.DataFrame, venue: str) -> pd.DataFrame:
    if history is None or history.empty:
        return _empty()
    out = history.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    out = out[out["date"] < CHAIN_GENESIS].copy()
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(pd.to_numeric(out["close_usd"], errors="coerce") > 0) & (pd.to_numeric(out["volume_usd"], errors="coerce") >= 0)]
    # The exchange ticker was DYDX. Before native-chain genesis, that ticker
    # can only refer to the original Ethereum token; relabel to the explicit
    # PIT identity ETHDYDX so it can never be stitched to native DYDX later.
    out["symbol"] = "ETHDYDX"
    out["source"] = f"pre_genesis_ethdydx__{venue}"
    return out[COLS].drop_duplicates("date", keep="last").sort_values("date")


def spans_historical_snapshot_window(history: pd.DataFrame) -> bool:
    if history is None or history.empty:
        return False
    dates = pd.to_datetime(history["date"], errors="coerce").dropna()
    if dates.empty:
        return False
    return bool(
        dates.min() <= CMC_FIRST_SNAPSHOT
        and dates.max() >= CMC_LAST_PRE_GENESIS_SNAPSHOT
        and dates.max() < CHAIN_GENESIS
    )


def run(outdir: Path) -> dict:
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    outdir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})

    probes = []
    histories = []
    for venue, fetcher in (("gateio_usdt", exchange.fetch_gate), ("kucoin_usdt", exchange.fetch_kucoin)):
        raw, raw_status = fetcher(session, "DYDX")
        bounded = bound_pre_genesis(raw, venue)
        spans = spans_historical_snapshot_window(bounded)
        probes.append({
            "venue": venue,
            "exchange_ticker": "DYDX",
            "pit_identity": "ETHDYDX",
            "raw_status": raw_status,
            "bounded_rows": int(len(bounded)),
            "first_date": str(bounded["date"].min().date()) if not bounded.empty else None,
            "last_date": str(bounded["date"].max().date()) if not bounded.empty else None,
            "spans_pre_genesis_snapshot_window": spans,
        })
        if not bounded.empty:
            histories.append(bounded)
        print(f"DYDX_PRE_GENESIS {venue} rows={len(bounded)} spans={spans} raw_status={raw_status}", flush=True)

    master = pd.concat(histories, ignore_index=True) if histories else _empty()
    master.to_csv(outdir / "DYDX_PRE_GENESIS_HISTORY.csv.gz", index=False, compression="gzip")
    pd.DataFrame(probes).to_csv(outdir / "DYDX_PRE_GENESIS_EVIDENCE.csv", index=False)

    usable_venues = [row["venue"] for row in probes if row["spans_pre_genesis_snapshot_window"]]
    payload = {
        "schema": "gate_btc.dydx_pre_genesis_probe.v1",
        "status": "PASS_EVIDENCE_ONLY",
        "chain_genesis": str(CHAIN_GENESIS.date()),
        "cmc_pre_genesis_identity": "ETHDYDX",
        "exchange_ticker": "DYDX",
        "usable_venues": usable_venues,
        "pre_genesis_only": True,
        "post_genesis_native_recovery_attempted": False,
        "cross_token_stitching": False,
        "native_dydx_continuity_assumed": False,
        "integration_eligible": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    (outdir / "DYDX_PRE_GENESIS_SUMMARY.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True), flush=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    run(args.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
