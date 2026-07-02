from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.workspace_cleanup_dry_run import build_workspace_cleanup_dry_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS workspace cleanup dry-run report.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--apply-low-risk", action="store_true", help="Remove only untracked low-risk candidates. Default is dry-run only.")
    args = parser.parse_args(argv)

    result = build_workspace_cleanup_dry_run(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root,
        apply_low_risk=bool(args.apply_low_risk),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
