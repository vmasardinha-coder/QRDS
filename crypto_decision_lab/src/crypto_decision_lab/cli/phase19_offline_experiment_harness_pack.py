from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase19_offline_experiment_harness_pack import build_phase19_offline_experiment_harness_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 19 Offline Experiment Harness Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--min-eligible-rows-per-coin", type=int, default=3500)
    args = parser.parse_args(argv)
    result = build_phase19_offline_experiment_harness_pack(
        Path(args.output_dir),
        args.repo_root or None,
        min_eligible_rows_per_coin=args.min_eligible_rows_per_coin,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
