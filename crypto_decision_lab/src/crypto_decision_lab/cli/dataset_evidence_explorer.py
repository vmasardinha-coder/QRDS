from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_evidence_explorer import build_dataset_evidence_explorer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Dataset Evidence Explorer.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--scan-report", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--max-files", type=int, default=150)
    args = parser.parse_args(argv)
    result = build_dataset_evidence_explorer(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        scan_report=args.scan_report or None,
        repo_root=args.repo_root or None,
        max_files=args.max_files,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
