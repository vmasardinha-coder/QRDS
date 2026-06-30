"""Full offline research CLI runner for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This CLI runs the current canonical research chain:

OKX fixture -> public batch -> cache -> pipeline -> walk-forward -> baseline
-> hypothetical backtest -> edge report -> export -> integration health.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from crypto_decision_lab.backtests.skeleton import build_walk_forward_backtest_report
from crypto_decision_lab.contracts.research import (
    build_contract_freeze_registry,
    build_integration_health_report,
    build_research_safety_stamp,
    validate_contract_freeze_registry,
    validate_integration_health_report,
)
from crypto_decision_lab.data.cache import (
    build_public_data_cache_index,
    load_public_candle_batch_cache,
    write_public_candle_batch_cache,
)
from crypto_decision_lab.data.okx_public import (
    build_okx_public_adapter_report,
    build_okx_public_candle_batch,
    load_okx_public_payload_fixture,
)
from crypto_decision_lab.data.public_adapter import (
    build_public_data_adapter_report,
    normalize_public_candle_batch,
)
from crypto_decision_lab.models.baseline import build_baseline_walk_forward_report
from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.reports.edge import build_edge_report_v1, summarize_edge_report_for_console, validate_edge_report_v1
from crypto_decision_lab.reports.export import (
    load_edge_report_artifacts,
    validate_edge_report_export_index,
    write_edge_report_artifacts,
)
from crypto_decision_lab.validation.walk_forward import (
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
)

FULL_RESEARCH_CLI_SUMMARY_SCHEMA_VERSION = "qrds.full_research_cli_summary.v1"

DEFAULT_FIXTURE_PATH = Path("data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json")


class FullResearchCliError(ValueError):
    """Raised when the full research CLI runner cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return str(path)


def parse_horizons(value: str | Sequence[int]) -> tuple[int, ...]:
    """Parse CLI horizons from comma-separated string or int sequence."""
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if not parts:
            raise FullResearchCliError("At least one horizon must be provided.")
        horizons = tuple(int(part) for part in parts)
    else:
        horizons = tuple(int(part) for part in value)

    if not horizons:
        raise FullResearchCliError("At least one horizon must be provided.")

    if any(horizon <= 0 for horizon in horizons):
        raise FullResearchCliError("Horizons must be positive integers.")

    if tuple(sorted(set(horizons))) != horizons:
        raise FullResearchCliError("Horizons must be unique and sorted ascending.")

    return horizons


def infer_return_column(rows: list[dict[str, Any]], horizons: tuple[int, ...]) -> str:
    """Infer the first available future_return column for the research chain."""
    if not rows:
        raise FullResearchCliError("Cannot infer return column from empty dataset.")

    preferred = [f"future_return_h{horizon}" for horizon in horizons]
    keys = rows[0].keys()

    for column in preferred:
        if column in keys:
            return column

    for column in sorted(keys):
        if column.startswith("future_return"):
            return column

    raise FullResearchCliError("No future_return column found in dataset rows.")


def validate_full_research_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the final CLI summary."""
    issues: list[dict[str, Any]] = []

    if summary.get("schema") != FULL_RESEARCH_CLI_SUMMARY_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_FULL_RESEARCH_SUMMARY_SCHEMA",
                "severity": "error",
                "message": "Invalid full research summary schema.",
            }
        )

    if summary.get("full_research_cli_passed") is not True:
        issues.append(
            {
                "code": "FULL_RESEARCH_CLI_NOT_PASSED",
                "severity": "error",
                "message": "Full research CLI did not pass.",
            }
        )

    for flag in (
        "operational_decision_allowed",
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "orders_allowed",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
    ):
        if summary.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_FULL_RESEARCH_SUMMARY_FLAG",
                    "severity": "error",
                    "flag": flag,
                    "message": f"Unsafe summary flag {flag}=True.",
                }
            )

    return issues


def run_full_research_chain(
    *,
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
    output_dir: str | Path,
    run_id: str = "full-research-run",
    report_id: str = "edge-report",
    horizons: tuple[int, ...] = (1, 3),
    train_size: int = 4,
    test_size: int = 2,
    step_size: int = 1,
    gap_size: int = 0,
    pipeline_commit: str = "full-research-cli",
    tags: Sequence[str] = ("full-research-cli",),
) -> dict[str, Any]:
    """Run the canonical offline full research chain and export artifacts."""
    horizons = parse_horizons(horizons)

    for name, value in (
        ("train_size", train_size),
        ("test_size", test_size),
        ("step_size", step_size),
        ("gap_size", gap_size),
    ):
        if value < 0:
            raise FullResearchCliError(f"{name} cannot be negative.")
    if train_size <= 0 or test_size <= 0 or step_size <= 0:
        raise FullResearchCliError("train_size, test_size and step_size must be positive.")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    fixture = load_okx_public_payload_fixture(Path(fixture_path))

    okx_report = build_okx_public_adapter_report(
        fixture["payload"],
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )
    batch = build_okx_public_candle_batch(
        fixture["payload"],
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )
    public_report = build_public_data_adapter_report(batch)

    cache_record = write_public_candle_batch_cache(batch, cache_dir=root / "cache")
    cache_index = build_public_data_cache_index(root / "cache")
    cached_batch = load_public_candle_batch_cache(cache_record["cache_item_dir"])
    candles = normalize_public_candle_batch(cached_batch)

    pipeline_run = run_research_pipeline(
        candles=candles,
        symbol=cached_batch["symbol"],
        interval=cached_batch["interval"],
        source=cached_batch["source"],
        output_dir=root / "runs",
        expected_interval_ms=cached_batch["expected_interval_ms"],
        pipeline_commit=pipeline_commit,
        run_id=run_id,
        horizons=horizons,
        tags=list(tags),
    )

    rows = load_research_dataset_jsonl(pipeline_run["paths"]["jsonl_path"])
    return_column = infer_return_column(rows, horizons)

    splits = build_walk_forward_splits(
        rows,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        gap_size=gap_size,
    )
    walk_forward_report = build_walk_forward_report(
        rows,
        splits,
        split_name="full-research-cli",
    )
    baseline_report = build_baseline_walk_forward_report(
        rows,
        splits,
        target_column=return_column,
    )
    backtest_report = build_walk_forward_backtest_report(
        rows,
        splits,
        return_column=return_column,
    )
    edge_report = build_edge_report_v1(
        backtest_report=backtest_report,
        baseline_report=baseline_report,
        walk_forward_report=walk_forward_report,
        dataset_row_count=len(rows),
        target_or_return_column=return_column,
        notes="generated by full offline research CLI",
    )

    edge_export_index = write_edge_report_artifacts(
        edge_report,
        output_dir=root / "edge_exports",
        report_id=report_id,
    )
    loaded_edge_artifacts = load_edge_report_artifacts(edge_export_index["index_path"])

    registry = build_contract_freeze_registry()
    health_report = build_integration_health_report(
        {
            "okx_report": okx_report,
            "public_report": public_report,
            "cache_record": cache_record,
            "cache_index": cache_index,
            "pipeline_report": pipeline_run["reports"]["pipeline"],
            "walk_forward_report": walk_forward_report,
            "baseline_report": baseline_report,
            "backtest_report": backtest_report,
            "edge_report": edge_report,
            "edge_export_index": edge_export_index,
            "edge_summary": loaded_edge_artifacts["summary"],
            "contract_freeze_registry": registry,
        },
        report_name="full-research-cli",
    )

    edge_issues = validate_edge_report_v1(edge_report)
    export_issues = validate_edge_report_export_index(edge_export_index)
    registry_issues = validate_contract_freeze_registry(registry)
    health_issues = validate_integration_health_report(health_report)

    validation_error_count = sum(
        1
        for issue in [*edge_issues, *export_issues, *registry_issues, *health_issues]
        if issue["severity"] == "error"
    )

    if validation_error_count:
        raise FullResearchCliError(
            "Full research chain produced validation errors: "
            f"{edge_issues + export_issues + registry_issues + health_issues}"
        )

    summary = {
        "schema": FULL_RESEARCH_CLI_SUMMARY_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "full_research_cli_passed": True,
        "fixture_path": str(fixture_path),
        "output_dir": str(root),
        "run_id": run_id,
        "report_id": report_id,
        "symbol": cached_batch["symbol"],
        "interval": cached_batch["interval"],
        "source": cached_batch["source"],
        "horizons": list(horizons),
        "dataset_row_count": len(rows),
        "split_count": len(splits),
        "return_column": return_column,
        "edge_status": edge_report["edge_status"],
        "edge_score": edge_report["edge_score"]["score"],
        "pipeline_jsonl_path": pipeline_run["paths"]["jsonl_path"],
        "edge_report_path": edge_export_index["report_path"],
        "edge_summary_path": edge_export_index["summary_path"],
        "edge_export_index_path": edge_export_index["index_path"],
        "integration_health_passed": health_report["integration_health_passed"],
        "validation_error_count": validation_error_count,
        **build_research_safety_stamp(),
    }

    summary_issues = validate_full_research_summary(summary)
    if any(issue["severity"] == "error" for issue in summary_issues):
        raise FullResearchCliError(f"Full research summary validation errors: {summary_issues}")

    _write_json(root / "contract_freeze_registry.json", registry)
    _write_json(root / "integration_health_report.json", health_report)
    _write_json(root / "full_research_summary.json", summary)
    _write_json(root / "edge_console_summary.json", summarize_edge_report_for_console(edge_report))

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-full-research",
        description="Run the QRDS full offline research chain.",
    )
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE_PATH), help="OKX public fixture path.")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated artifacts.")
    parser.add_argument("--run-id", default="full-research-run", help="Research pipeline run id.")
    parser.add_argument("--report-id", default="edge-report", help="Edge export report id.")
    parser.add_argument("--horizons", default="1,3", help="Comma-separated target horizons.")
    parser.add_argument("--train-size", type=int, default=4, help="Walk-forward train size.")
    parser.add_argument("--test-size", type=int, default=2, help="Walk-forward test size.")
    parser.add_argument("--step-size", type=int, default=1, help="Walk-forward step size.")
    parser.add_argument("--gap-size", type=int, default=0, help="Walk-forward gap size.")
    parser.add_argument("--pipeline-commit", default="full-research-cli", help="Pipeline commit marker.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    summary = run_full_research_chain(
        fixture_path=args.fixture,
        output_dir=args.output_dir,
        run_id=args.run_id,
        report_id=args.report_id,
        horizons=parse_horizons(args.horizons),
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        gap_size=args.gap_size,
        pipeline_commit=args.pipeline_commit,
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
