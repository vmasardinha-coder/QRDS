from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase36_unified_risk_regime_research_portal_shell_pack import build_phase36_unified_risk_regime_research_portal_shell_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 36 Unified Risk/Regime Research Portal Shell Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    result = build_phase36_unified_risk_regime_research_portal_shell_pack(Path(args.output_dir), args.repo_root or None)
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
