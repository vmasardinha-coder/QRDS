#!/usr/bin/env python3
"""Audit a local D50 checkpoint pack against the published GitHub status mirror.

This tool is deliberately read-only with respect to both D50 ledgers and runtime
status.  It can emit only a reconciliation audit manifest.  A PASS result means
that a separately reviewed mirror-status update may be prepared; it is never an
authorization to rewrite frozen economic rows, count historical backfill, place
orders, use capital, or promote a strategy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


CORE_STRATEGIES = {
    "D50_CONTROL": "CONTROL",
    "D50_COST_AWARE": "PRIMARY_PROMOTION_ELIGIBLE",
    "D50_EXIT_2SIGMA": "EXPLORATORY",
}
OPTIONAL_STRATEGIES = {"D50_COST_AWARE_VOL20"}
MAX_FIRST_RETRIEVAL_LAG = timedelta(hours=24)
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

REQUIRED_LEDGER_COLUMNS = {
    "record_type",
    "observation_number",
    "strategy",
    "role",
    "date",
    "bar_close_at_utc",
    "gate_anchor_utc",
    "first_retrieved_at_utc",
    "gross_return",
    "trading_cost_return",
    "funding_return",
    "net_return",
    "equity_from_anchor",
    "turnover",
    "gross_long",
    "gross_short_abs",
    "net_exposure",
    "kill_switch_active",
    "vol_scale",
    "source_bar_sha256",
    "replay_row_sha256",
    "status",
    "orders",
    "capital",
}

DECIMAL_COLUMNS = {
    "gross_return",
    "trading_cost_return",
    "funding_return",
    "net_return",
    "equity_from_anchor",
    "turnover",
    "gross_long",
    "gross_short_abs",
    "net_exposure",
    "vol_scale",
    "orders",
    "capital",
}
INTEGER_COLUMNS = {"observation_number"}
BOOLEAN_COLUMNS = {"kill_switch_active"}
NULL_TOKENS = {"", "nan", "none", "null", "na"}


class ReconciliationError(RuntimeError):
    """Fail-closed validation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ReconciliationError(f"expected JSON object: {path}")
    return payload


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ReconciliationError(f"CSV has no header: {path}")
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ReconciliationError(f"invalid boolean {field}={value!r}")


def parse_decimal(value: Any, field: str, allow_null: bool = False) -> Decimal | None:
    text = str(value).strip()
    if allow_null and text.lower() in NULL_TOKENS:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ReconciliationError(f"invalid numeric {field}={value!r}") from exc


def require_zero(value: Any, field: str) -> None:
    parsed = parse_decimal(value, field)
    if parsed != 0:
        raise ReconciliationError(f"safety invariant changed: {field}={value!r}")


def parse_datetime(value: Any, field: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ReconciliationError(f"invalid timestamp {field}={value!r}") from exc
    if parsed.tzinfo is None:
        raise ReconciliationError(f"timestamp lacks UTC offset: {field}={value!r}")
    return parsed.astimezone(timezone.utc)


def parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ReconciliationError(f"invalid date {field}={value!r}") from exc


def validate_local_status(status: dict[str, Any]) -> None:
    if status.get("research_only") is not True:
        raise ReconciliationError("local status is not research_only=true")
    if status.get("operational_status") != "NOT_APPROVED":
        raise ReconciliationError("local operational_status must be NOT_APPROVED")
    require_zero(status.get("orders"), "local.orders")
    require_zero(status.get("capital"), "local.capital")
    if "shadow_only" in status and status.get("shadow_only") is not True:
        raise ReconciliationError("local shadow_only invariant changed")
    if "not_approved" in status and status.get("not_approved") is not True:
        raise ReconciliationError("local not_approved invariant changed")
    if status.get("historical_backfill_counted_as_prospective") is not False:
        raise ReconciliationError("historical backfill must never count as prospective")


def validate_remote_status(status: dict[str, Any]) -> dict[str, Any]:
    if status.get("schema") != "gate_btc.d50_measurement_status.v1":
        raise ReconciliationError(f"unexpected remote D50 schema: {status.get('schema')!r}")
    if status.get("research_only") is not True or status.get("shadow_only") is not True:
        raise ReconciliationError("remote research/shadow safety invariant changed")
    if status.get("not_approved") is not True or status.get("promotion_allowed") is not False:
        raise ReconciliationError("remote approval/promotion safety invariant changed")
    require_zero(status.get("orders_generated"), "remote.orders_generated")
    require_zero(status.get("real_capital_used"), "remote.real_capital_used")
    ledger = status.get("prospective_immutable_ledger")
    if not isinstance(ledger, dict):
        raise ReconciliationError("remote prospective_immutable_ledger is missing")
    if ledger.get("frozen_history_must_be_preserved") is not True:
        raise ReconciliationError("remote frozen-history invariant changed")
    if ledger.get("mutation_performed") is not False:
        raise ReconciliationError("remote mirror reports a forbidden mutation")
    try:
        current = int(ledger["current"])
        target = int(ledger["target"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReconciliationError("remote current/target counter is invalid") from exc
    if current < 0 or target <= 0:
        raise ReconciliationError("remote current/target counter is invalid")
    return ledger


def _canonical_cell(column: str, value: Any) -> Any:
    text = "" if value is None else str(value).strip()
    if column in INTEGER_COLUMNS:
        try:
            return int(text)
        except ValueError as exc:
            raise ReconciliationError(f"invalid integer {column}={value!r}") from exc
    if column in BOOLEAN_COLUMNS:
        return parse_bool(value, column)
    if column in DECIMAL_COLUMNS:
        return parse_decimal(value, column, allow_null=(column == "vol_scale"))
    return None if text.lower() in NULL_TOKENS else text


def canonical_row(row: dict[str, Any], columns: Iterable[str]) -> tuple[tuple[str, Any], ...]:
    return tuple((column, _canonical_cell(column, row.get(column))) for column in columns)


def validate_local_ledger(
    status: dict[str, Any], fieldnames: list[str], rows: list[dict[str, str]]
) -> dict[str, Any]:
    missing = REQUIRED_LEDGER_COLUMNS.difference(fieldnames)
    if missing:
        raise ReconciliationError(f"local ledger missing columns: {sorted(missing)}")
    if not rows:
        raise ReconciliationError("local D50 ledger is empty")

    unknown = {row.get("strategy", "") for row in rows}.difference(
        set(CORE_STRATEGIES) | OPTIONAL_STRATEGIES
    )
    if unknown:
        raise ReconciliationError(f"unexpected D50 strategies: {sorted(unknown)}")

    core_rows = [row for row in rows if row.get("strategy") in CORE_STRATEGIES]
    if not core_rows:
        raise ReconciliationError("local D50 ledger has no core prospective rows")

    key_seen: set[tuple[str, str]] = set()
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    anchor_values: set[str] = set()

    for row in core_rows:
        strategy = row["strategy"]
        row_date = row["date"]
        key = (row_date, strategy)
        if key in key_seen:
            raise ReconciliationError(f"duplicate prospective row: {row_date} {strategy}")
        key_seen.add(key)
        by_date[row_date].append(row)

        if row.get("role") != CORE_STRATEGIES[strategy]:
            raise ReconciliationError(f"role mismatch for {row_date} {strategy}")
        if row.get("status") != "ADMITTED_BY_FROZEN_GATE":
            raise ReconciliationError(f"non-admitted core row: {row_date} {strategy}")
        require_zero(row.get("orders"), f"ledger.orders[{row_date},{strategy}]")
        require_zero(row.get("capital"), f"ledger.capital[{row_date},{strategy}]")

        parse_date(row_date, "ledger.date")
        close_at = parse_datetime(row.get("bar_close_at_utc"), "bar_close_at_utc")
        anchor = parse_datetime(row.get("gate_anchor_utc"), "gate_anchor_utc")
        retrieved = parse_datetime(row.get("first_retrieved_at_utc"), "first_retrieved_at_utc")
        if close_at <= anchor:
            raise ReconciliationError(f"row is not post-gate: {row_date} {strategy}")
        if retrieved < close_at or retrieved - close_at > MAX_FIRST_RETRIEVAL_LAG:
            raise ReconciliationError(f"row violates <=24h first-retrieval rule: {row_date} {strategy}")
        anchor_values.add(str(row.get("gate_anchor_utc")).strip())

        for hash_field in ("source_bar_sha256", "replay_row_sha256"):
            if not HEX64.fullmatch(str(row.get(hash_field, "")).strip()):
                raise ReconciliationError(f"invalid {hash_field}: {row_date} {strategy}")

    if len(anchor_values) != 1:
        raise ReconciliationError("core ledger contains multiple gate anchors")
    if status.get("gate_anchor_utc") and str(status.get("gate_anchor_utc")).strip() not in anchor_values:
        raise ReconciliationError("local status gate anchor differs from frozen ledger anchor")

    sorted_dates = sorted(by_date, key=lambda value: parse_date(value, "ledger.date"))
    observation_numbers: list[int] = []
    for row_date in sorted_dates:
        day_rows = by_date[row_date]
        strategies = {row["strategy"] for row in day_rows}
        if strategies != set(CORE_STRATEGIES):
            raise ReconciliationError(
                f"unpaired core date {row_date}: expected {sorted(CORE_STRATEGIES)}, got {sorted(strategies)}"
            )
        numbers = {int(row["observation_number"]) for row in day_rows}
        if len(numbers) != 1:
            raise ReconciliationError(f"inconsistent observation number on {row_date}")
        observation_numbers.append(next(iter(numbers)))
        source_hashes = {row["source_bar_sha256"] for row in day_rows}
        if len(source_hashes) != 1:
            raise ReconciliationError(f"strategies do not share one source-bar hash on {row_date}")

    expected_numbers = list(range(1, len(sorted_dates) + 1))
    if observation_numbers != expected_numbers:
        raise ReconciliationError(
            f"observation sequence is not contiguous from 1: {observation_numbers}"
        )

    try:
        paired = int(status["paired_prospective_observations"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReconciliationError("local paired_prospective_observations is invalid") from exc
    if paired != len(sorted_dates):
        raise ReconciliationError(
            f"local status/ledger count mismatch: status={paired} ledger={len(sorted_dates)}"
        )
    if status.get("first_prospective_date") != sorted_dates[0]:
        raise ReconciliationError("local first_prospective_date does not match ledger")
    if status.get("latest_prospective_date") != sorted_dates[-1]:
        raise ReconciliationError("local latest_prospective_date does not match ledger")

    excluded = {str(item) for item in status.get("excluded_historical_backfill_dates", [])}
    overlap = excluded.intersection(sorted_dates)
    if overlap:
        raise ReconciliationError(
            f"historical backfill was counted as prospective: {sorted(overlap)}"
        )

    return {
        "paired_observations": paired,
        "first_date": sorted_dates[0],
        "latest_date": sorted_dates[-1],
        "core_row_count": len(core_rows),
        "excluded_backfill_dates": sorted(excluded),
        "gate_anchor_utc": next(iter(anchor_values)),
    }


def validate_prior_prefix(
    prior_fieldnames: list[str],
    prior_rows: list[dict[str, str]],
    local_fieldnames: list[str],
    local_rows: list[dict[str, str]],
    expected_remote_count: int,
) -> dict[str, Any]:
    if set(prior_fieldnames) != set(local_fieldnames):
        raise ReconciliationError("prior/local ledger schemas differ")
    prior_core = [row for row in prior_rows if row.get("strategy") in CORE_STRATEGIES]
    prior_dates = {row.get("date") for row in prior_core}
    if len(prior_dates) != expected_remote_count:
        raise ReconciliationError(
            f"prior ledger does not prove remote prefix: prior={len(prior_dates)} remote={expected_remote_count}"
        )

    local_index: dict[tuple[str, str], dict[str, str]] = {}
    for row in local_rows:
        key = (str(row.get("date")), str(row.get("strategy")))
        if key in local_index:
            raise ReconciliationError(f"duplicate local key while checking frozen prefix: {key}")
        local_index[key] = row

    for prior in prior_rows:
        key = (str(prior.get("date")), str(prior.get("strategy")))
        current = local_index.get(key)
        if current is None:
            raise ReconciliationError(f"frozen prior row disappeared: {key}")
        if canonical_row(prior, prior_fieldnames) != canonical_row(current, prior_fieldnames):
            raise ReconciliationError(f"frozen prior row changed: {key}")

    return {
        "prior_row_count": len(prior_rows),
        "prior_paired_observations": len(prior_dates),
        "frozen_prefix_preserved": True,
    }


def parse_repair_result(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def validate_repair_result(path: Path) -> dict[str, Any]:
    values = parse_repair_result(path)
    if not values.get("STATUS", "").startswith("PASS"):
        raise ReconciliationError("repair result does not report PASS")
    if values.get("FROZEN_ROWS_PRESERVED", "").lower() != "true":
        raise ReconciliationError("repair result does not prove frozen-row preservation")
    if values.get("RESEARCH_ONLY", "").lower() != "true":
        raise ReconciliationError("repair result lost research-only invariant")
    if values.get("OPERATIONAL_STATUS") != "NOT_APPROVED":
        raise ReconciliationError("repair result operational status is not NOT_APPROVED")
    require_zero(values.get("ORDERS"), "repair_result.ORDERS")
    require_zero(values.get("CAPITAL"), "repair_result.CAPITAL")
    return {
        "status": values["STATUS"],
        "frozen_rows_preserved": True,
    }


def validate_diagnostics(path: Path, local_keys: set[tuple[str, str]]) -> dict[str, Any]:
    files = sorted(path.glob("*.json")) if path.is_dir() else []
    if not files:
        raise ReconciliationError("source-revision diagnostics are required but missing")
    hashes: list[dict[str, str]] = []
    for diagnostic_path in files:
        payload = load_json(diagnostic_path)
        required = {
            "status": "PASS_PROVENANCE_ONLY_FROZEN_ROW_PRESERVED",
            "economic_fields_identical": True,
            "source_revision_detected": True,
            "frozen_row_preserved": True,
            "mutation_performed": False,
            "counter_incremented_for_existing_date": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
        }
        for field, expected in required.items():
            if payload.get(field) != expected:
                raise ReconciliationError(
                    f"invalid source-revision diagnostic {diagnostic_path.name}: {field}={payload.get(field)!r}"
                )
        require_zero(payload.get("orders"), f"{diagnostic_path.name}.orders")
        require_zero(payload.get("capital"), f"{diagnostic_path.name}.capital")
        key = (str(payload.get("date")), str(payload.get("strategy")))
        if key not in local_keys:
            raise ReconciliationError(
                f"source-revision diagnostic does not reference a frozen local row: {key}"
            )
        hashes.append({"file": diagnostic_path.name, "sha256": sha256_file(diagnostic_path)})
    return {"count": len(files), "files": hashes}


def build_audit(
    *,
    local_status_path: Path,
    local_ledger_path: Path,
    remote_status_path: Path,
    prior_ledger_path: Path | None = None,
    diagnostics_dir: Path | None = None,
    repair_result_path: Path | None = None,
) -> dict[str, Any]:
    local_status = load_json(local_status_path)
    remote_status = load_json(remote_status_path)
    local_fieldnames, local_rows = load_csv(local_ledger_path)

    validate_local_status(local_status)
    remote_ledger = validate_remote_status(remote_status)
    local_summary = validate_local_ledger(local_status, local_fieldnames, local_rows)

    remote_current = int(remote_ledger["current"])
    local_current = int(local_summary["paired_observations"])
    if remote_current > local_current:
        raise ReconciliationError(
            f"remote mirror leads local checkpoint: remote={remote_current} local={local_current}"
        )
    if remote_status.get("data_as_of"):
        if parse_date(remote_status["data_as_of"], "remote.data_as_of") > parse_date(
            local_summary["latest_date"], "local.latest_date"
        ):
            raise ReconciliationError("remote data_as_of is newer than local checkpoint")

    source_revision_blocked = bool(remote_ledger.get("source_revision_only")) and str(
        remote_ledger.get("status", "")
    ).startswith("BLOCKED_LOCAL_SOURCE_REVISION")

    prior_summary: dict[str, Any] | None = None
    diagnostics_summary: dict[str, Any] | None = None
    repair_summary: dict[str, Any] | None = None

    if source_revision_blocked:
        if prior_ledger_path is None:
            raise ReconciliationError("prior ledger is required to prove the frozen remote prefix")
        if diagnostics_dir is None:
            raise ReconciliationError("source-revision diagnostics directory is required")
        if repair_result_path is None:
            raise ReconciliationError("final repair result is required")

    if prior_ledger_path is not None:
        prior_fieldnames, prior_rows = load_csv(prior_ledger_path)
        prior_summary = validate_prior_prefix(
            prior_fieldnames,
            prior_rows,
            local_fieldnames,
            local_rows,
            remote_current,
        )
    if diagnostics_dir is not None:
        local_keys = {(str(row.get("date")), str(row.get("strategy"))) for row in local_rows}
        diagnostics_summary = validate_diagnostics(diagnostics_dir, local_keys)
    if repair_result_path is not None:
        repair_summary = validate_repair_result(repair_result_path)

    status = (
        "PASS_MIRROR_ALREADY_ALIGNED"
        if local_current == remote_current
        else "PASS_MIRROR_ADVANCE_CANDIDATE"
    )
    return {
        "schema": "gate_btc.d50_mirror_reconciliation_audit.v1",
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_only": True,
        "runtime_mutation_performed": False,
        "economic_row_mutation_allowed": False,
        "historical_backfill_counted_as_prospective": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "remote_mirror": {
            "current": remote_current,
            "target": int(remote_ledger["target"]),
            "data_as_of": remote_status.get("data_as_of"),
            "status": remote_ledger.get("status"),
            "sha256": sha256_file(remote_status_path),
        },
        "local_checkpoint": {
            **local_summary,
            "status": local_status.get("status"),
            "ledger_sha256": sha256_file(local_ledger_path),
            "status_sha256": sha256_file(local_status_path),
        },
        "frozen_prefix_evidence": prior_summary,
        "source_revision_evidence": diagnostics_summary,
        "repair_evidence": repair_summary,
        "required_next_action": (
            "separately review and publish a status-mirror advancement only; "
            "do not rewrite or import economic rows from this audit output"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-status", type=Path, required=True)
    parser.add_argument("--local-ledger", type=Path, required=True)
    parser.add_argument("--remote-status", type=Path, required=True)
    parser.add_argument("--prior-ledger", type=Path)
    parser.add_argument("--diagnostics-dir", type=Path)
    parser.add_argument("--repair-result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        audit = build_audit(
            local_status_path=args.local_status,
            local_ledger_path=args.local_ledger,
            remote_status_path=args.remote_status,
            prior_ledger_path=args.prior_ledger,
            diagnostics_dir=args.diagnostics_dir,
            repair_result_path=args.repair_result,
        )
    except ReconciliationError as exc:
        print(f"D50_MIRROR_RECONCILIATION=FAIL_CLOSED: {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"D50_MIRROR_RECONCILIATION={audit['status']}")
    print(f"AUDIT_OUTPUT={args.output}")
    print("ORDERS=0")
    print("CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
