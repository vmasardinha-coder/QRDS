from __future__ import annotations
import argparse, json
from pathlib import Path
from crypto_decision_lab.reports.phase11_canonical_promotion_dry_run_lock_pack import build_phase11_canonical_promotion_dry_run_lock_pack

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build QRDS Phase 11 Canonical Promotion Dry-Run Lock Pack.")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--repo-root", default="")
    a = p.parse_args(argv)
    result = build_phase11_canonical_promotion_dry_run_lock_pack(Path(a.output_dir), a.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
