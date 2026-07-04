from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase16_multisource_consensus_baseline_pack import build_phase16_multisource_consensus_baseline_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 16 Multi-source Consensus Baseline Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--min-common-rows-per-coin", type=int, default=4000)
    args = parser.parse_args(argv)
    result = build_phase16_multisource_consensus_baseline_pack(
        Path(args.output_dir),
        args.repo_root or None,
        min_common_rows_per_coin=args.min_common_rows_per_coin,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
