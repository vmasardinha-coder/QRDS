from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.foundation_checkpoint_next_phase import build_foundation_checkpoint_next_phase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Foundation Checkpoint / Next Phase Gate.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)

    result = build_foundation_checkpoint_next_phase(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root or None,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
