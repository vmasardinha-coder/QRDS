"""Command line entry point for autonomous GATE BTC data readiness."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import traceback

from .config import DEFAULT_INPUT_RELATIVE, DEFAULT_RUNTIME_RELATIVE
from .finalize import build_independent_audit_package
from .okx_client import OKXPublicDailyClient
from .repair import repair_historical_master
from .snapshot import collect_prospective_snapshot, evaluate_qualification
from .gate_btc_d50_data_review_reporting import documentary_adjudication, reporting_lines


def _repo_root(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src/crypto_decision_lab").exists():
            return candidate
    raise RuntimeError("Repository root not found.")


def _downloads() -> Path:
    return Path.home() / "Downloads"


def _write_report(lines: list[str], prefix: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _downloads() / f"{prefix}_{stamp}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["repair", "snapshot", "daily", "status"])
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)

    root = _repo_root(args.repo_root)
    runtime = root / DEFAULT_RUNTIME_RELATIVE
    client = OKXPublicDailyClient()

    report_lines = [
        "GATE BTC DATA READINESS",
        f"COMMAND={args.command}",
        f"STARTED_AT={datetime.now(timezone.utc).isoformat()}",
        f"REPO_ROOT={root}",
        "PROJECT_FILES_MODIFIED=0",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
    ]

    try:
        result: dict
        if args.command == "repair":
            result = repair_historical_master(
                master_path=root / DEFAULT_INPUT_RELATIVE,
                output_root=runtime / "historical_repair",
                client=client,
            )
        elif args.command == "snapshot":
            result = collect_prospective_snapshot(runtime_root=runtime, client=client)
        elif args.command == "status":
            result = evaluate_qualification(runtime)
        else:
            repair_status_path = runtime / "historical_repair/ingestion_repair_status.json"
            if not repair_status_path.exists():
                repair_historical_master(
                    master_path=root / DEFAULT_INPUT_RELATIVE,
                    output_root=runtime / "historical_repair",
                    client=client,
                )
            snapshot = collect_prospective_snapshot(runtime_root=runtime, client=client)
            qualification = evaluate_qualification(runtime)
            package = build_independent_audit_package(
                repo_root=root,
                runtime_root=runtime,
                downloads_dir=_downloads(),
            )
            result = {"snapshot": snapshot, "qualification": qualification, "package": package}

        # Reporting only: preserve frozen qualification/config flags and engine.
        adjudication = documentary_adjudication(
            contract_path=root / "gate_btc_inputs/candidate_contract_v32.json",
            v32_zip_path=root / "gate_btc_inputs/GATE_BTC_D50_7D_V32_RATIFICATION_2026-07-30.zip",
        )
        result = {**result, "current_documentary_adjudication": adjudication}
        report_lines.extend(reporting_lines(adjudication))
        report_lines.append("STATUS=PASS")
        report_lines.append("RESULT_JSON=" + json.dumps(result, sort_keys=True, ensure_ascii=False))
        report_lines.append(f"FINISHED_AT={datetime.now(timezone.utc).isoformat()}")
        report = _write_report(report_lines, "GATE_BTC_DATA_READINESS_REPORT")
        print(json.dumps({"status": "PASS", "report": str(report), "result": result}, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        report_lines.extend(
            [
                "STATUS=ERROR",
                f"ERROR_TYPE={type(exc).__name__}",
                f"ERROR_MESSAGE={exc}",
                "ERROR_FULL=" + traceback.format_exc().replace("\n", "\\n"),
                f"FINISHED_AT={datetime.now(timezone.utc).isoformat()}",
            ]
        )
        report = _write_report(report_lines, "GATE_BTC_DATA_READINESS_ERROR")
        print(json.dumps({"status": "ERROR", "report": str(report), "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
