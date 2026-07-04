from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase14_okx_public_data_adapter_pack import build_phase14_okx_public_data_adapter_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 14 OKX Public Data Adapter Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--inst-ids", default="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP")
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--rows-per-instrument", type=int, default=5000)
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)
    inst_ids = [x.strip().upper() for x in args.inst_ids.split(",") if x.strip()]
    result = build_phase14_okx_public_data_adapter_pack(
        Path(args.output_dir),
        args.repo_root or None,
        inst_ids=inst_ids,
        bar=args.bar,
        rows_per_instrument=args.rows_per_instrument,
        fetch=not args.no_fetch,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
