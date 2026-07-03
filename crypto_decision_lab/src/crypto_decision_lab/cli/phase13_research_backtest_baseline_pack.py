from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase13_research_backtest_baseline_pack import build_phase13_research_backtest_baseline_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 13 Research Backtest Baseline Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    result = build_phase13_research_backtest_baseline_pack(Path(args.output_dir), args.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
