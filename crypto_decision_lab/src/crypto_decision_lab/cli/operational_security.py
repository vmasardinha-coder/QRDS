"""CLI for QRDS/QOS operational security review gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.operational_security import SecurityConfig, generate_operational_security_gate


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the QRDS operational security review gate packet.")
    parser.add_argument("--output-dir", default="artifacts/operational_security", help="Output directory for generated artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated symbols for the research packet.")
    parser.add_argument("--reports", default="", help="Comma-separated upstream JSON report paths.")
    parser.add_argument("--api-key-present", action="store_true", help="Record unsafe state: API key present. Should remain false.")
    parser.add_argument("--api-key-required", action="store_true", help="Record unsafe state: API key required. Should remain false.")
    parser.add_argument("--account-connection-required", action="store_true", help="Record unsafe state: exchange account connection required.")
    parser.add_argument("--authenticated-connection-used", action="store_true", help="Record unsafe state: authenticated exchange connection used.")
    parser.add_argument("--execution-layer-present", action="store_true", help="Record unsafe state: execution layer present.")
    parser.add_argument("--order-endpoint-present", action="store_true", help="Record unsafe state: order endpoint present.")
    parser.add_argument("--binance-mode", default="SIMULATION_FIXTURE_REPLAY", help="Binance adapter mode. Must remain SIMULATION_FIXTURE_REPLAY.")
    parser.add_argument("--okx-mode", default="PUBLIC_CACHE_OFFLINE", help="OKX adapter mode. Must remain public/cache/offline only.")
    parser.add_argument("--bybit-mode", default="BLOCKED_PENDING", help="Bybit adapter mode. Must remain blocked/pending.")
    parser.add_argument("--secrets-scan-state", default="PASS", choices=["NOT_RUN", "PASS", "FAIL"], help="Secrets/API-key scan state.")
    parser.add_argument(
        "--security-state",
        default="UNDER_REVIEW",
        choices=["NOT_STARTED", "UNDER_REVIEW", "APPROVED_RESEARCH_ONLY"],
        help="Research-only operational security review state.",
    )
    parser.add_argument("--policy-lock", default="ACTIVE", choices=["ACTIVE", "INACTIVE"], help="Policy lock state. Must remain ACTIVE.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SecurityConfig(
        api_key_present=bool(args.api_key_present),
        api_key_required=bool(args.api_key_required),
        account_connection_required=bool(args.account_connection_required),
        authenticated_connection_used=bool(args.authenticated_connection_used),
        execution_layer_present=bool(args.execution_layer_present),
        order_endpoint_present=bool(args.order_endpoint_present),
        binance_mode=args.binance_mode,
        okx_mode=args.okx_mode,
        bybit_mode=args.bybit_mode,
        secrets_scan_state=args.secrets_scan_state,
        security_state=args.security_state,
        policy_lock=args.policy_lock,
    )
    index = generate_operational_security_gate(
        output_dir=Path(args.output_dir),
        symbols=_split_csv(args.symbols) or ["BTC-USDT"],
        report_paths=_split_csv(args.reports),
        config=config,
    )
    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    print()
    print(f"[QRDS 8V] Operational Security Review Gate generated: {index['html_path']}")
    print("[QRDS 8V] Scope: research security review only; no API key, no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
