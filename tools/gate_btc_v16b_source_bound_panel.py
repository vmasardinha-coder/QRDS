#!/usr/bin/env python3
"""Bind the deterministic V16B feature panel to a frozen SIGNAL source manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools import gate_btc_v16b_feature_panel as panel


def build(daily: Path, universe: Path, source_manifest_path: Path):
    source = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source.get("schema") != "gate_btc.v16b.signal_market_source_manifest.v1":
        raise ValueError("invalid SIGNAL market-source manifest schema")
    if source.get("daily_prices_sha256") != panel.sha256_file(daily):
        raise ValueError("SIGNAL source manifest daily_prices_sha256 mismatch")
    if source.get("weekly_universe_sha256") != panel.sha256_file(universe):
        raise ValueError("SIGNAL source manifest weekly_universe_sha256 mismatch")
    if source.get("market_venue") != "BINANCE_SPOT_USDT" or source.get("benchmark") != "BTCUSDT":
        raise ValueError("unexpected frozen SIGNAL market venue/benchmark")
    out, manifest = panel.build_panel(daily, universe)
    manifest["signal_market_source_manifest_sha256"] = panel.sha256_file(source_manifest_path)
    manifest["signal_market_source_contract_sha256"] = source.get("contract_sha256")
    manifest["signal_market_source_signal_date"] = source.get("signal_date")
    return out, manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--daily-prices", required=True)
    p.add_argument("--weekly-universe", required=True)
    p.add_argument("--signal-market-source-manifest", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    out_path, manifest_path = Path(a.output), Path(a.manifest)
    out, manifest = build(Path(a.daily_prices), Path(a.weekly_universe), Path(a.signal_market_source_manifest))
    out_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, lineterminator="\n")
    manifest["panel_sha256"] = panel.sha256_file(out_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status":"OK","panel_sha256":manifest["panel_sha256"],"source_manifest_sha256":manifest["signal_market_source_manifest_sha256"],"ORDERS":0,"REAL_CAPITAL":0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
