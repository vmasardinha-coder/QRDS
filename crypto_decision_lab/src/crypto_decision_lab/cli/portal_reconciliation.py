from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.portal_reconciliation import build_portal_reconciliation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Portal Reconciliation / Unified Launcher Map.")
    parser.add_argument("--output-dir", default="artifacts/portal_reconciliation")
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args(argv)

    result = build_portal_reconciliation(output_dir=Path(args.output_dir), repo_root=args.repo_root)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
