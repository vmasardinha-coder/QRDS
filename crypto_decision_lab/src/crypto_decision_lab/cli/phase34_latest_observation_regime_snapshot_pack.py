from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase34_latest_observation_regime_snapshot_pack import build_phase34_latest_observation_regime_snapshot_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 34 Latest Observation + Regime Snapshot Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    result = build_phase34_latest_observation_regime_snapshot_pack(Path(args.output_dir), args.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
