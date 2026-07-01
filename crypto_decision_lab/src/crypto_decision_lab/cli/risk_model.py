"""CLI for QRDS/QOS risk model gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.risk_model import RiskConfig, generate_risk_model_gate


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _float_or_none(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the QRDS risk model gate packet.")
    parser.add_argument("--output-dir", default="artifacts/risk_model", help="Output directory for generated artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated symbols for the research packet.")
    parser.add_argument("--reports", default="", help="Comma-separated upstream JSON report paths.")
    parser.add_argument("--max-portfolio-drawdown-pct", default=None, help="Explicit portfolio drawdown limit percentage.")
    parser.add_argument("--max-symbol-exposure-pct", default=None, help="Explicit per-symbol exposure cap percentage.")
    parser.add_argument("--daily-loss-limit-pct", default=None, help="Explicit simulated daily loss limit percentage.")
    parser.add_argument("--stress-loss-limit-pct", default=None, help="Explicit stress loss budget percentage.")
    parser.add_argument("--kill-switch-present", action="store_true", help="Record that kill-switch design is documented.")
    parser.add_argument("--liquidity-check-present", action="store_true", help="Record that liquidity constraints are documented.")
    parser.add_argument("--cost-model-present", action="store_true", help="Record that cost/slippage model is attached.")
    parser.add_argument("--risk-artifact-present", action="store_true", help="Record that a formal risk artifact is attached.")
    parser.add_argument(
        "--risk-state",
        default="NOT_STARTED",
        choices=["NOT_STARTED", "DRAFT", "UNDER_REVIEW", "APPROVED_RESEARCH_ONLY"],
        help="Research-only risk review state.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = RiskConfig(
        max_portfolio_drawdown_pct=_float_or_none(args.max_portfolio_drawdown_pct),
        max_symbol_exposure_pct=_float_or_none(args.max_symbol_exposure_pct),
        daily_loss_limit_pct=_float_or_none(args.daily_loss_limit_pct),
        stress_loss_limit_pct=_float_or_none(args.stress_loss_limit_pct),
        kill_switch_present=bool(args.kill_switch_present),
        liquidity_check_present=bool(args.liquidity_check_present),
        cost_model_present=bool(args.cost_model_present),
        risk_artifact_present=bool(args.risk_artifact_present),
        risk_state=args.risk_state,
    )
    index = generate_risk_model_gate(
        output_dir=Path(args.output_dir),
        symbols=_split_csv(args.symbols) or ["BTC-USDT"],
        report_paths=_split_csv(args.reports),
        config=config,
    )
    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    print()
    print(f"[QRDS 8U] Risk Model Gate generated: {index['html_path']}")
    print("[QRDS 8U] Scope: research risk review only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
