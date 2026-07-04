from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase25_volatility_feature_baseline_strengthening_pack import build_phase25_volatility_feature_baseline_strengthening_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 25 Volatility Feature Baseline Strengthening Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--min-rows-per-coin", type=int, default=3500)
    args = parser.parse_args(argv)
    result = build_phase25_volatility_feature_baseline_strengthening_pack(Path(args.output_dir), args.repo_root or None, min_rows_per_coin=args.min_rows_per_coin)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
