"""CLI for QRDS Multi-Asset Report Aggregator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.full_research import run_full_research_chain
from crypto_decision_lab.fixtures.okx_public_catalog import build_okx_public_fixture_catalog
from crypto_decision_lab.reports.multi_asset import write_multi_asset_report
from crypto_decision_lab.reports.pack import write_research_report_pack


def _safe_symbol(symbol: str) -> str:
    return symbol.strip().lower().replace("/", "-").replace("_", "-").replace(" ", "-").replace("-", "_")


def _parse_symbols(value: str | None) -> tuple[str, ...] | None:
    if value is None or not value.strip():
        return None
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())


def run_multi_asset_report_from_fixtures(
    *,
    fixture_dir: str | Path,
    output_dir: str | Path,
    symbols: tuple[str, ...] | None = None,
    report_name: str = "qrds-multi-asset-report",
) -> dict:
    """Run full research + report pack per fixture and aggregate."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    catalog = build_okx_public_fixture_catalog(fixture_dir, symbols=symbols)

    pack_index_paths: list[str] = []
    for entry in catalog["entries"]:
        symbol_id = _safe_symbol(entry["instId"])
        full_dir = root / "full_research" / symbol_id
        pack_dir = root / "report_packs" / symbol_id

        run_full_research_chain(
            fixture_path=entry["path"],
            output_dir=full_dir,
            run_id=f"multi-asset-{symbol_id}",
            report_id=f"edge-{symbol_id}",
            horizons=(1, 3),
            train_size=4,
            test_size=2,
            step_size=1,
            pipeline_commit="multi-asset-report-aggregator",
            tags=["multi-asset-report", entry["instId"]],
        )
        pack_index = write_research_report_pack(
            full_research_dir=full_dir,
            output_dir=pack_dir,
            pack_name=f"report-pack-{symbol_id}",
        )
        pack_index_paths.append(pack_index["index_path"])

    return write_multi_asset_report(
        pack_index_paths=pack_index_paths,
        output_dir=root / "multi_asset_report",
        report_name=report_name,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-multi-asset-report",
        description="Generate a QRDS multi-asset research report from local fixtures.",
    )
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--symbols", default=None, help="Optional comma-separated symbols, e.g. BTC-USDT,ETH-USDT.")
    parser.add_argument("--report-name", default="qrds-multi-asset-report", help="Report name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = run_multi_asset_report_from_fixtures(
        fixture_dir=args.fixture_dir,
        output_dir=args.output_dir,
        symbols=_parse_symbols(args.symbols),
        report_name=args.report_name,
    )

    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
