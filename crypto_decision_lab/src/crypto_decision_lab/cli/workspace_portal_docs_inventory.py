from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.workspace_portal_docs_inventory import build_workspace_portal_docs_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Workspace / Portal / Docs Inventory Map.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--max-items", type=int, default=500)
    args = parser.parse_args(argv)
    result = build_workspace_portal_docs_inventory(
        output_dir=Path(args.output_dir),
        repo_root=Path(args.repo_root),
        max_items=args.max_items,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
