from __future__ import annotations
import argparse, json
from pathlib import Path
from crypto_decision_lab.reports.phase13_binance_hyperliquid_source_comparison_pack import build_phase13_binance_hyperliquid_source_comparison_pack

def main(argv=None):
    p = argparse.ArgumentParser(description="Build QRDS Phase 13 Binance Hyperliquid Source Comparison Pack.")
    p.add_argument("--output-dir", required=True); p.add_argument("--repo-root", default="")
    a = p.parse_args(argv)
    r = build_phase13_binance_hyperliquid_source_comparison_pack(Path(a.output_dir), a.repo_root or None)
    print(json.dumps({k:v for k,v in r.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
