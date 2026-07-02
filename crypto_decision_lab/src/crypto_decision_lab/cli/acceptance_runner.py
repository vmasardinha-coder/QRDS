from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.acceptance_runner import build_acceptance_runner


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Acceptance Runner report.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--pytest-status", default="NOT_RUN")
    parser.add_argument("--refresh-status", default="NOT_RUN")
    parser.add_argument("--git-status-file", default="")
    args = parser.parse_args(argv)

    result = build_acceptance_runner(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_csv(args.reports) or None,
        pytest_status=args.pytest_status,
        refresh_status=args.refresh_status,
        git_status_text=_read_text(args.git_status_file),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
