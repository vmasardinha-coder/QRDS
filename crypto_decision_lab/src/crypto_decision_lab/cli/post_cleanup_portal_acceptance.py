from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.post_cleanup_portal_acceptance import build_post_cleanup_portal_acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Post-Cleanup Portal Acceptance report.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)

    result = build_post_cleanup_portal_acceptance(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root or None,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
