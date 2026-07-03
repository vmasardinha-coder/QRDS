from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.portal_unification_suite import build_portal_unification_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS unified portal launcher suite.")
    parser.add_argument("--output-dir", default="artifacts/unified_portal_suite")
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    result = build_portal_unification_suite(output_dir=Path(args.output_dir), repo_root=args.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
