from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_offline_sample_intake_promotion_pack import build_phase10_offline_sample_intake_promotion_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 10 Offline Sample Intake / Promotion Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)

    result = build_phase10_offline_sample_intake_promotion_pack(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root or None,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
