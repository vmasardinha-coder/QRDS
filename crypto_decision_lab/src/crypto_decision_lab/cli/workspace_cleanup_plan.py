from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.workspace_cleanup_plan import build_workspace_cleanup_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS workspace cleanup plan.")
    parser.add_argument("--output-dir", default="artifacts/workspace_cleanup_plan")
    args = parser.parse_args(argv)
    result = build_workspace_cleanup_plan(output_dir=Path(args.output_dir))
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
