from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase17_consensus_quality_drift_monitor_pack import build_phase17_consensus_quality_drift_monitor_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 17 Consensus Quality Drift Monitor Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--outlier-deviation-bps", type=float, default=50.0)
    parser.add_argument("--max-outlier-rate", type=float, default=0.05)
    parser.add_argument("--max-p95-dispersion-bps", type=float, default=100.0)
    parser.add_argument("--min-rows-per-coin", type=int, default=4000)
    args = parser.parse_args(argv)
    result = build_phase17_consensus_quality_drift_monitor_pack(
        Path(args.output_dir),
        args.repo_root or None,
        outlier_deviation_bps=args.outlier_deviation_bps,
        max_outlier_rate=args.max_outlier_rate,
        max_p95_dispersion_bps=args.max_p95_dispersion_bps,
        min_rows_per_coin=args.min_rows_per_coin,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
