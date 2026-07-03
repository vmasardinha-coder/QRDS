from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.installer_archive_safe_apply import build_installer_archive_safe_apply


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Installer Archive Safe Apply report.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Generate report without moving files.")
    args = parser.parse_args(argv)
    result = build_installer_archive_safe_apply(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root,
        apply=not args.dry_run,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
