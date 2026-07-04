from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase24_volatility_residual_diagnostics_baseline_robustness_pack import build_phase24_volatility_residual_diagnostics_baseline_robustness_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 24 Volatility Residual Diagnostics Baseline Robustness Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    result = build_phase24_volatility_residual_diagnostics_baseline_robustness_pack(Path(args.output_dir), args.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
