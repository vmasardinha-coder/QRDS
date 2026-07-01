"""CLI for QRDS workspace housekeeping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.ops.housekeeping import build_workspace_housekeeping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QRDS workspace housekeeping report")
    parser.add_argument("--repo-root", default="..", help="QRDS repo root. Default assumes execution from crypto_decision_lab/.")
    parser.add_argument("--output-dir", default="artifacts/workspace_housekeeping")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean-artifacts", action="store_true", help="Also remove generated artifacts directories. Default is false for safety.")
    parser.add_argument("--no-gitignore-update", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_workspace_housekeeping(
        Path(args.repo_root),
        args.output_dir,
        dry_run=args.dry_run,
        clean_artifacts=args.clean_artifacts,
        update_gitignore=not args.no_gitignore_update,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True, ensure_ascii=False))
    print(f"\n[QRDS 9A] Workspace Housekeeping generated: {result.html_path}")
    print("[QRDS 9A] Scope: local workspace hygiene only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
