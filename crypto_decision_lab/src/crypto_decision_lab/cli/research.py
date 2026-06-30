"""Offline research CLI for QRDS.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This CLI runs the research pipeline from a local candle fixture file.

Example:
python -m crypto_decision_lab.cli.research \
  --input-candles data/fixtures/dql_sample_candles.json \
  --output-dir ./runs \
  --symbol BTC-USDT \
  --interval 1h \
  --source local_fixture \
  --run-id demo-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_CLI_SCHEMA_VERSION = "qrds.research_cli.v1"


class ResearchCliError(ValueError):
    """Raised when the offline research CLI cannot run safely."""


def _assert_safe_context() -> dict[str, Any]:
    """Assert the available safety flags are compatible with research-only CLI use.

    Some safety contexts expose only operational-risk flags, while app_mode is
    carried by reports/artifacts. The CLI therefore blocks on any unsafe flag
    and stamps its own outputs as INTERACTIVE_RESEARCH_ONLY.
    """
    safe = build_safe_context()

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if safe.get(flag) is True:
            raise ResearchCliError(f"CLI blocked: unsafe flag {flag}=True.")

    return safe


def load_candle_fixture(path: str | Path) -> dict[str, Any]:
    """Load candles from a local JSON fixture.

    Supported shapes:

    1. Object fixture:
       {
         "symbol": "BTC-USDT",
         "interval": "1h",
         "source": "unit_test",
         "candles": [...]
       }

    2. Raw list fixture:
       [...]
    """
    fixture_path = Path(path)

    if not fixture_path.exists() or not fixture_path.is_file():
        raise ResearchCliError(f"Input candle fixture not found: {fixture_path}")

    with fixture_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        candles = payload
        metadata: dict[str, Any] = {}
    elif isinstance(payload, dict):
        candles = payload.get("candles")
        metadata = {
            "symbol": payload.get("symbol"),
            "interval": payload.get("interval"),
            "source": payload.get("source"),
        }
    else:
        raise ResearchCliError("Input candle fixture must be a JSON object or list.")

    if not isinstance(candles, list) or not candles:
        raise ResearchCliError("Input candle fixture has no candles.")

    return {
        "candles": candles,
        "symbol": metadata.get("symbol"),
        "interval": metadata.get("interval"),
        "source": metadata.get("source"),
    }


def build_cli_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Build a compact research-only CLI summary."""
    safe = _assert_safe_context()

    summary = {
        "schema": RESEARCH_CLI_SCHEMA_VERSION,
        "run_id": run.get("run_id"),
        "symbol": run.get("symbol"),
        "interval": run.get("interval"),
        "source": run.get("source"),
        "regime": run.get("regime"),
        "dql_score": run.get("dql_score"),
        "dataset_row_count": run.get("dataset_row_count"),
        "pipeline_quality_passed": run.get("reports", {}).get("pipeline", {}).get("pipeline_quality_passed"),
        "paths": run.get("paths", {}),
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert summary[flag] == safe[flag]

    return summary


def write_cli_summary(summary: dict[str, Any], output_dir: str | Path, run_id: str) -> str:
    """Write the CLI summary beside the research run output."""
    summary_path = Path(output_dir) / run_id / "cli_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return str(summary_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-research",
        description="Run a QRDS offline research pipeline from a local candle fixture.",
    )

    parser.add_argument("--input-candles", required=True, help="Path to local candle fixture JSON.")
    parser.add_argument("--output-dir", required=True, help="Directory where research run artifacts will be written.")
    parser.add_argument("--symbol", default=None, help="Symbol override. Example: BTC-USDT.")
    parser.add_argument("--interval", default=None, help="Interval override. Example: 1h.")
    parser.add_argument("--source", default=None, help="Source override. Example: local_fixture.")
    parser.add_argument("--run-id", default=None, help="Optional deterministic run id.")
    parser.add_argument("--pipeline-commit", default="unknown", help="Pipeline commit or version label.")
    parser.add_argument("--expected-interval-ms", type=int, default=3_600_000, help="Expected candle interval in milliseconds.")
    parser.add_argument("--horizons", default="1,3", help="Comma-separated positive horizons. Default: 1,3.")
    parser.add_argument("--up-threshold", type=float, default=0.02, help="Future return threshold for up labels.")
    parser.add_argument("--down-threshold", type=float, default=-0.02, help="Future return threshold for down labels.")
    parser.add_argument("--registry-name", default="qrds-research-run-registry", help="Registry name.")
    parser.add_argument("--tag", action="append", default=None, help="Optional tag. Can be used more than once.")
    parser.add_argument("--notes", default=None, help="Optional run notes.")

    return parser


def parse_horizons(value: str) -> tuple[int, ...]:
    """Parse comma-separated horizons."""
    try:
        horizons = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise ResearchCliError("Horizons must be comma-separated integers.") from exc

    if not horizons or any(h <= 0 for h in horizons):
        raise ResearchCliError("Horizons must contain positive integers.")

    return horizons


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    _assert_safe_context()

    parser = build_parser()
    args = parser.parse_args(argv)

    fixture = load_candle_fixture(args.input_candles)

    symbol = args.symbol or fixture.get("symbol")
    interval = args.interval or fixture.get("interval")
    source = args.source or fixture.get("source")

    if not symbol:
        raise ResearchCliError("symbol is required, either in fixture or --symbol.")
    if not interval:
        raise ResearchCliError("interval is required, either in fixture or --interval.")
    if not source:
        raise ResearchCliError("source is required, either in fixture or --source.")

    horizons = parse_horizons(args.horizons)

    run = run_research_pipeline(
        candles=fixture["candles"],
        symbol=symbol,
        interval=interval,
        source=source,
        output_dir=args.output_dir,
        expected_interval_ms=args.expected_interval_ms,
        pipeline_commit=args.pipeline_commit,
        run_id=args.run_id,
        horizons=horizons,
        up_threshold=args.up_threshold,
        down_threshold=args.down_threshold,
        registry_name=args.registry_name,
        tags=args.tag,
        notes=args.notes,
    )

    summary = build_cli_summary(run)
    summary_path = write_cli_summary(summary, args.output_dir, run["run_id"])
    summary["paths"]["cli_summary_path"] = summary_path

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def run() -> None:
    """Console-safe wrapper."""
    try:
        raise SystemExit(main())
    except ResearchCliError as exc:
        print(f"QRDS research CLI error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    run()
