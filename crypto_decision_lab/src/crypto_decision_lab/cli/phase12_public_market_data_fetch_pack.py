from __future__ import annotations
import argparse, json
from pathlib import Path
from crypto_decision_lab.reports.phase12_public_market_data_fetch_pack import build_phase12_public_market_data_fetch_pack

def main(argv=None):
    p = argparse.ArgumentParser(description="Build QRDS Phase 12 Public Market Data Fetch Pack.")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--repo-root", default="")
    p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    p.add_argument("--interval", default="1h")
    p.add_argument("--rows-per-symbol", type=int, default=5000)
    p.add_argument("--no-fetch", action="store_true")
    a = p.parse_args(argv)
    symbols = [x.strip().upper() for x in a.symbols.split(",") if x.strip()]
    r = build_phase12_public_market_data_fetch_pack(Path(a.output_dir), a.repo_root or None, symbols=symbols, interval=a.interval, rows_per_symbol=a.rows_per_symbol, fetch=not a.no_fetch)
    print(json.dumps({k:v for k,v in r.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
