#!/usr/bin/env python3
"""Deterministic physical-evidence preflight for the GATE BTC 2.0 dataset.

This tool reads a clean ``gate-btc-runtime`` checkout, verifies the exact bytes
that are physically present, and classifies them before an official dataset
descriptor can be authored.  It never creates a descriptor or a seal, never
feeds an engine, and never treats a status document or a hash-only reference as
the underlying dataset.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_2_official_dataset_manifest import (
        canonical_hash,
        validate_contract,
    )
except ModuleNotFoundError:  # Direct execution: python tools/<script>.py
    from gate_btc_2_official_dataset_manifest import (  # type: ignore[no-redef]
        canonical_hash,
        validate_contract,
    )


SCHEMA = "gate_btc.2_0.official_evidence_inventory.v1"
STATUS = "BLOCKED_NO_ADMISSIBLE_OFFICIAL_DATASET_CANDIDATE"
ASSESSMENT_KIND = "PHYSICAL_EVIDENCE_PREFLIGHT_NOT_A_DATASET_DESCRIPTOR_OR_SEAL"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_SCOPES = [
    "BTC_CORE",
    "D50_ECONOMIC",
    "D50_QUALIFIED",
    "MULTIASSET_V2A",
]

CLASS_STATUS = "STATUS_ONLY_NOT_DATASET"
CLASS_BLOCKED = "BLOCKED_INCOMPLETE"
CLASS_STALE = "BLOCKED_STALE_UNSEALED"
CLASS_AUXILIARY = "AUXILIARY_POINT_IN_TIME_ONLY"
CLASS_DUPLICATE = "DUPLICATE_ALIAS"

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "economic_calibration_performed": False,
    "official_dataset_descriptor_created": False,
    "official_dataset_sealed": False,
    "official_challenger_runs_executed": 0,
    "canonical_data_writes": 0,
    "runtime_mutations": 0,
    "incumbent_mutations": 0,
}

TABULAR_SUFFIXES = (".csv", ".csv.gz", ".jsonl", ".parquet")
V2A_ARCHIVE_RE = re.compile(
    r"^runtime/data_quality/v2a/archives/.+\."
    r"(?:coingecko_current_universe|data_quality_summary|download_failures)\.csv\.gz$"
)
GATEWAY_ARCHIVE_RE = re.compile(
    r"^runtime/universe_snapshots/gateway/archives/.+\.scanner_top500_raw\.csv\.gz$"
)
QMASTER_PATHS = {
    "runtime/GATE_BTC_QMASTER_LATEST.csv",
    "runtime/qmaster/GATE_BTC_QMASTER_LATEST.csv",
}
ISOLATED_TABULAR_PREFIXES = (
    "runtime/ledgers/bull_replay_live_shadow/",
    "runtime/ledgers/delta_paper_monitor/",
)
ECONOMIC_RESEARCH_INPUT_PATHS = {
    "research_inputs/V16B_SELECTED_SHORTS_2026_11W.csv",
    "research_inputs/V9C_SELECTED_SHORTS_2026_WINDOW.csv",
}

MANUAL_MARKET_SPECS: dict[str, dict[str, str]] = {
    "BINANCE_SPOT": {
        "path": "crypto_decision_lab/manual_intake/inbox/{asset_lower}_usdt_binance_public_klines_1h.csv",
        "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
        "symbol": "{asset}-USDT",
        "interval_field": "interval",
        "interval": "1h",
    },
    "HYPERLIQUID_PERP": {
        "path": "crypto_decision_lab/manual_intake/hyperliquid_inbox/{asset_lower}_hyperliquid_public_candles_1h.csv",
        "source": "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY",
        "symbol": "{asset}-USDC-PERP",
        "interval_field": "interval",
        "interval": "1h",
    },
    "OKX_SWAP": {
        "path": "crypto_decision_lab/manual_intake/okx_inbox/{asset_lower}_usdt_swap_okx_public_candles_1h.csv",
        "source": "OKX_PUBLIC_CANDLES_RESEARCH_ONLY",
        "symbol": "{asset}-USDT-SWAP",
        "interval_field": "bar",
        "interval": "1h",
    },
    "BYBIT_LINEAR": {
        "path": "crypto_decision_lab/manual_intake/bybit_inbox/{asset_lower}_usdt_bybit_public_linear_klines_1h.csv",
        "source": "BYBIT_LINEAR_PUBLIC_KLINES_RESEARCH_ONLY",
        "symbol": "{asset}-USDT-PERP",
        "interval_field": "interval",
        "interval": "1h",
    },
}
MANUAL_MARKET_PATHS = {
    spec["path"].format(asset=asset, asset_lower=asset.lower())
    for spec in MANUAL_MARKET_SPECS.values()
    for asset in ("BTC", "ETH", "SOL")
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git object ID


def _canonical_self_hash(payload: dict[str, Any], field: str) -> str:
    unsigned = dict(payload)
    unsigned.pop(field, None)
    return canonical_hash(unsigned)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _safe_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    _require(bool(relative) and not rel.is_absolute(), f"unsafe runtime path: {relative!r}")
    _require(".." not in rel.parts, f"unsafe runtime path: {relative!r}")
    root_resolved = root.resolve()
    candidate = root / rel
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise RuntimeError(f"required runtime evidence missing: {relative}") from exc
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise RuntimeError(f"runtime evidence escapes root: {relative}") from exc
    _require(not candidate.is_symlink() and resolved.is_file(), f"unsafe runtime evidence: {relative}")
    current = candidate.parent
    while current != root and current != current.parent:
        _require(not current.is_symlink(), f"symlinked runtime parent: {relative}")
        current = current.parent
    return resolved


def _load_json(root: Path, relative: str) -> tuple[dict[str, Any], bytes]:
    raw = _safe_file(root, relative).read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON evidence: {relative}") from exc
    _require(isinstance(payload, dict), f"expected JSON object: {relative}")
    return payload, raw


def _verify_self_hash(payload: dict[str, Any], field: str, label: str) -> None:
    claimed = payload.get(field)
    _require(HEX64.fullmatch(str(claimed)) is not None, f"invalid {label} {field}")
    _require(claimed == _canonical_self_hash(payload, field), f"{label} {field} mismatch")


def _verify_research_boundary(payload: dict[str, Any], label: str) -> None:
    expectations = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    for field, expected in expectations.items():
        _require(payload.get(field) == expected, f"unsafe {label} field {field}")


def _artifact(
    root: Path,
    relative: str,
    *,
    classification: str,
    evidence_role: str,
    scope: str | None,
    observed_or_derived: str,
    source_snapshot_id: str | None = None,
    duplicate_of: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _safe_file(root, relative).read_bytes()
    result: dict[str, Any] = {
        "path": relative,
        "byte_length": len(raw),
        "sha256": _sha256(raw),
        "git_blob_sha1": _git_blob_sha1(raw),
        "classification": classification,
        "evidence_role": evidence_role,
        "scope": scope,
        "observed_or_derived": observed_or_derived,
    }
    if source_snapshot_id is not None:
        result["source_snapshot_id"] = source_snapshot_id
    if duplicate_of is not None:
        result["duplicate_of"] = duplicate_of
    if extra:
        result.update(extra)
    return result


def _read_gzip_csv(root: Path, relative: str) -> tuple[bytes, list[str], list[dict[str, str]]]:
    compressed = _safe_file(root, relative).read_bytes()
    try:
        raw = gzip.decompress(compressed)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise RuntimeError(f"corrupt gzip evidence: {relative}") from exc
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(f"invalid compressed CSV evidence: {relative}") from exc
    _require(bool(columns) and len(columns) == len(set(columns)), f"invalid CSV header: {relative}")
    _require(all(None not in row for row in rows), f"malformed CSV row: {relative}")
    return raw, columns, rows


def _read_csv(root: Path, relative: str) -> tuple[list[str], list[dict[str, str]]]:
    raw = _safe_file(root, relative).read_bytes()
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise RuntimeError(f"invalid CSV evidence: {relative}") from exc
    _require(bool(columns) and len(columns) == len(set(columns)), f"invalid CSV header: {relative}")
    _require(all(None not in row for row in rows), f"malformed CSV row: {relative}")
    return columns, rows


def _validate_readiness(readiness: dict[str, Any]) -> None:
    _require(readiness.get("schema") == "gate_btc.2_0.dataset_seal_readiness.v1", "readiness schema mismatch")
    _require(
        readiness.get("assessment_kind") == "READINESS_ONLY_NOT_A_DATASET_SEAL",
        "readiness boundary mismatch",
    )
    _verify_self_hash(readiness, "assessment_sha256", "readiness")
    tracks = readiness.get("tracks")
    _require(isinstance(tracks, dict) and sorted(tracks) == sorted(REQUIRED_SCOPES), "readiness tracks mismatch")
    for field, expected in {
        "stage_3_dataset_sealed": False,
        "official_challenger_runs_allowed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }.items():
        _require(readiness.get(field) == expected, f"unsafe readiness field {field}")


def _validate_v2a(root: Path, readiness: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = "runtime/data_quality/v2a"
    status_rel = f"{base}/STATUS.json"
    status, _ = _load_json(root, status_rel)
    _require(status.get("schema") == "gate_btc.v2a_point_in_time_data_ledger_status.v1", "V2A status schema mismatch")
    _verify_self_hash(status, "status_sha256", "V2A status")
    _verify_research_boundary(status, "V2A status")
    _require(status.get("feeds_frozen_engine") is False, "V2A status feeds frozen engine")
    _require(status.get("retrospective_backfill_allowed") is False, "V2A backfill boundary changed")

    snapshot_id = status.get("latest_snapshot_id")
    _require(isinstance(snapshot_id, str) and snapshot_id, "V2A latest snapshot missing")
    snapshot_rel = f"{base}/snapshots/{snapshot_id}.json"
    snapshot, _ = _load_json(root, snapshot_rel)
    _require(snapshot.get("schema") == "gate_btc.v2a_point_in_time_data_snapshot.v1", "V2A snapshot schema mismatch")
    _verify_self_hash(snapshot, "record_sha256", "V2A snapshot")
    _verify_research_boundary(snapshot, "V2A snapshot")
    _require(snapshot.get("snapshot_id") == snapshot_id, "V2A snapshot ID mismatch")
    _require(snapshot.get("source_run_id") == status.get("latest_source_run_id"), "V2A source run mismatch")
    _require(snapshot.get("source_data_as_of") == status.get("latest_source_data_as_of"), "V2A source date mismatch")
    _require(snapshot.get("retrospective_reconstruction") is False, "V2A retrospective reconstruction changed")

    artifacts = [
        _artifact(
            root,
            status_rel,
            classification=CLASS_STATUS,
            evidence_role="V2A_LEDGER_STATUS",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
            source_snapshot_id=snapshot_id,
        ),
        _artifact(
            root,
            snapshot_rel,
            classification=CLASS_STATUS,
            evidence_role="V2A_IMMUTABLE_SNAPSHOT_RECORD",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
            source_snapshot_id=snapshot_id,
        ),
    ]

    parsed: dict[str, tuple[bytes, list[str], list[dict[str, str]], str]] = {}
    roles = {
        "universe_archive": "V2A_POINT_IN_TIME_UNIVERSE",
        "quality_archive": "V2A_DATA_QUALITY_SUMMARY",
        "failures_archive": "V2A_DOWNLOAD_FAILURES",
    }
    for key, role in roles.items():
        metadata = snapshot.get(key)
        _require(isinstance(metadata, dict), f"V2A {key} metadata missing")
        archive_path = metadata.get("archive_path")
        _require(isinstance(archive_path, str) and archive_path, f"V2A {key} path missing")
        relative = f"{base}/{archive_path}"
        raw, columns, rows = _read_gzip_csv(root, relative)
        compressed = _safe_file(root, relative).read_bytes()
        _require(_sha256(compressed) == metadata.get("archive_sha256"), f"V2A archive hash mismatch: {relative}")
        _require(_sha256(raw) == metadata.get("raw_sha256"), f"V2A raw hash mismatch: {relative}")
        _require(len(raw) == metadata.get("raw_size_bytes"), f"V2A raw size mismatch: {relative}")
        parsed[key] = (raw, columns, rows, relative)
        artifacts.append(
            _artifact(
                root,
                relative,
                classification=CLASS_BLOCKED if key == "universe_archive" else CLASS_STATUS,
                evidence_role=role,
                scope="MULTIASSET_V2A",
                observed_or_derived="observed" if key == "universe_archive" else "derived",
                source_snapshot_id=snapshot_id,
                extra={
                    "compression": "gzip",
                    "uncompressed_byte_length": len(raw),
                    "uncompressed_sha256": _sha256(raw),
                    "csv_columns": columns,
                    "csv_row_count": len(rows),
                },
            )
        )

    _, universe_columns, universe_rows, _ = parsed["universe_archive"]
    _, quality_columns, quality_rows, _ = parsed["quality_archive"]
    _, failure_columns, failure_rows, _ = parsed["failures_archive"]
    _require(
        {"id", "symbol", "name", "market_cap_rank", "standard_ticker", "is_stable", "is_blocked"}.issubset(universe_columns),
        "V2A universe required columns missing",
    )
    _require(len(universe_rows) == snapshot.get("universe_row_count"), "V2A universe row count mismatch")
    _require(
        {"data_as_of", "attempted_symbols", "loaded_symbols", "failed_symbols", "coverage_ratio", "data_quality_status", "survivorship_bias_present"}.issubset(quality_columns),
        "V2A quality required columns missing",
    )
    _require(len(quality_rows) == 1, "V2A quality summary row count mismatch")
    _require({"symbol", "reason"}.issubset(failure_columns), "V2A failures required columns missing")
    _require(len(failure_rows) == snapshot.get("download_failure_row_count"), "V2A failure row count mismatch")
    quality = quality_rows[0]
    attempted = int(quality["attempted_symbols"])
    loaded = int(quality["loaded_symbols"])
    failed = int(quality["failed_symbols"])
    coverage = float(quality["coverage_ratio"])
    _require(attempted == loaded + failed, "V2A attempted count is inconsistent")
    _require(attempted == snapshot.get("attempted_symbols") == status.get("latest_attempted_symbols"), "V2A attempted mismatch")
    _require(loaded == snapshot.get("loaded_symbols") == status.get("latest_loaded_symbols"), "V2A loaded mismatch")
    _require(failed == snapshot.get("failed_symbols") == status.get("latest_failed_symbols"), "V2A failed mismatch")
    _require(math.isclose(coverage, float(snapshot.get("coverage_ratio")), abs_tol=1e-12), "V2A coverage mismatch")
    _require(math.isclose(coverage, float(status.get("latest_coverage_ratio")), abs_tol=1e-12), "V2A status coverage mismatch")
    _require(quality["survivorship_bias_present"].strip().lower() == "true", "V2A survivorship warning absent")
    _require(snapshot.get("survivorship_bias_present") is True, "V2A snapshot survivorship warning absent")
    _require(status.get("survivorship_bias_present") is True, "V2A status survivorship warning absent")

    readiness_blockers = list(readiness["tracks"]["MULTIASSET_V2A"].get("blockers", []))
    blockers = sorted(
        set(
            readiness_blockers
            + [
                "MULTIASSET_V2A_OFFICIAL_DESCRIPTOR_NOT_SUPPLIED",
                "MULTIASSET_V2A_PRICE_HISTORY_IS_DERIVED_CURRENT_COMPOSITION",
                "MULTIASSET_V2A_SOURCE_PROVENANCE_NOT_BOUND",
                "MULTIASSET_V2A_TABULAR_SCHEMA_NOT_BOUND",
                "V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE",
                "V2A_SURVIVORSHIP_BIAS_PRESENT",
                "V2A_SYMBOL_LOAD_GAP",
            ]
        )
    )
    summary = {
        "status": "BLOCKED_PHYSICAL_EVIDENCE_INCOMPLETE",
        "snapshot_id": snapshot_id,
        "source_data_as_of": snapshot.get("source_data_as_of"),
        "attempted_symbols": attempted,
        "loaded_symbols": loaded,
        "failed_symbols": failed,
        "coverage_ratio": coverage,
        "universe_rows": len(universe_rows),
        "survivorship_bias_present": True,
        "blockers": blockers,
    }
    return artifacts, summary


def _validate_gateway(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = "runtime/universe_snapshots/gateway"
    status_rel = f"{base}/STATUS.json"
    status, _ = _load_json(root, status_rel)
    _require(status.get("schema") == "gate_btc.gateway_point_in_time_universe_ledger_status.v1", "Gateway status schema mismatch")
    _verify_self_hash(status, "status_sha256", "Gateway status")
    _verify_research_boundary(status, "Gateway status")
    _require(status.get("feeds_frozen_engine") is False, "Gateway ledger feeds frozen engine")
    _require(status.get("retrospective_backfill_allowed") is False, "Gateway backfill boundary changed")

    snapshot_id = status.get("latest_snapshot_id")
    _require(isinstance(snapshot_id, str) and snapshot_id, "Gateway latest snapshot missing")
    snapshot_rel = f"{base}/snapshots/{snapshot_id}.json"
    snapshot, _ = _load_json(root, snapshot_rel)
    _require(snapshot.get("schema") == "gate_btc.gateway_point_in_time_universe_snapshot.v1", "Gateway snapshot schema mismatch")
    _verify_self_hash(snapshot, "record_sha256", "Gateway snapshot")
    _verify_research_boundary(snapshot, "Gateway snapshot")
    _require(snapshot.get("snapshot_id") == snapshot_id, "Gateway snapshot ID mismatch")
    _require(snapshot.get("source_run_id") == status.get("latest_source_run_id"), "Gateway source run mismatch")
    _require(snapshot.get("source_data_as_of") == status.get("latest_source_data_as_of"), "Gateway source date mismatch")
    _require(snapshot.get("retrospective_reconstruction") is False, "Gateway retrospective reconstruction changed")

    archive_path = snapshot.get("archive_path")
    _require(isinstance(archive_path, str) and archive_path, "Gateway archive path missing")
    archive_rel = f"{base}/{archive_path}"
    raw, columns, rows = _read_gzip_csv(root, archive_rel)
    compressed = _safe_file(root, archive_rel).read_bytes()
    _require(_sha256(compressed) == snapshot.get("archive_sha256"), "Gateway archive hash mismatch")
    _require(_sha256(raw) == snapshot.get("raw_csv_sha256") == status.get("latest_raw_csv_sha256"), "Gateway raw hash mismatch")
    _require(len(raw) == snapshot.get("raw_csv_size_bytes"), "Gateway raw size mismatch")
    _require(columns == snapshot.get("columns"), "Gateway CSV columns mismatch")
    _require(len(rows) == snapshot.get("row_count"), "Gateway CSV row count mismatch")
    _require({"base", "cg_rank", "cg_name", "cg_market_cap", "cg_volume"}.issubset(columns), "Gateway required columns missing")

    artifacts = [
        _artifact(
            root,
            status_rel,
            classification=CLASS_STATUS,
            evidence_role="GATEWAY_LEDGER_STATUS",
            scope=None,
            observed_or_derived="derived",
            source_snapshot_id=snapshot_id,
        ),
        _artifact(
            root,
            snapshot_rel,
            classification=CLASS_STATUS,
            evidence_role="GATEWAY_IMMUTABLE_SNAPSHOT_RECORD",
            scope=None,
            observed_or_derived="derived",
            source_snapshot_id=snapshot_id,
        ),
        _artifact(
            root,
            archive_rel,
            classification=CLASS_AUXILIARY,
            evidence_role="GATEWAY_POINT_IN_TIME_UNIVERSE",
            scope=None,
            observed_or_derived="observed",
            source_snapshot_id=snapshot_id,
            extra={
                "compression": "gzip",
                "uncompressed_byte_length": len(raw),
                "uncompressed_sha256": _sha256(raw),
                "csv_columns": columns,
                "csv_row_count": len(rows),
            },
        ),
    ]
    return artifacts, {
        "status": "AUXILIARY_ONLY_NOT_AN_ALLOWED_OFFICIAL_DATASET_SCOPE",
        "snapshot_id": snapshot_id,
        "source_data_as_of": snapshot.get("source_data_as_of"),
        "row_count": len(rows),
        "warning_failed_checks": snapshot.get("gateway_warning_failed_checks", []),
        "feeds_frozen_engine": False,
    }


def _validate_qmaster(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    descriptor_rel = "runtime/GATE_BTC_QMASTER_LATEST.txt"
    csv_rel = "runtime/GATE_BTC_QMASTER_LATEST.csv"
    alias_descriptor_rel = "runtime/qmaster/GATE_BTC_QMASTER_LATEST.txt"
    alias_csv_rel = "runtime/qmaster/GATE_BTC_QMASTER_LATEST.csv"
    descriptor, descriptor_raw = _load_json(root, descriptor_rel)
    _require(descriptor.get("schema") == "gate_btc.qmaster_export.v1", "QMASTER schema mismatch")
    _require(descriptor.get("status") == "PASS", "QMASTER export status mismatch")
    for field, expected in {
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changed": False,
    }.items():
        _require(descriptor.get(field) == expected, f"unsafe QMASTER field {field}")
    columns, rows = _read_csv(root, csv_rel)
    _require({"date", "symbol", "close_usd", "volume_usd", "source"}.issubset(columns), "QMASTER required columns missing")
    csv_raw = _safe_file(root, csv_rel).read_bytes()
    _require(_sha256(csv_raw) == descriptor.get("csv_sha256") == descriptor.get("source_member_sha256"), "QMASTER CSV hash mismatch")
    usable = [row for row in rows if row.get("date") and row.get("symbol")]
    _require(len(usable) == descriptor.get("rows"), "QMASTER row count mismatch")
    _require(len({row["symbol"].strip().upper() for row in usable}) == descriptor.get("symbols"), "QMASTER symbol count mismatch")
    _require(max(row["date"].strip()[:10] for row in usable) == descriptor.get("data_as_of"), "QMASTER data_as_of mismatch")

    alias_descriptor_raw = _safe_file(root, alias_descriptor_rel).read_bytes()
    alias_csv_raw = _safe_file(root, alias_csv_rel).read_bytes()
    _require(alias_descriptor_raw == descriptor_raw, "QMASTER descriptor alias differs")
    _require(alias_csv_raw == csv_raw, "QMASTER CSV alias differs")

    artifacts = [
        _artifact(
            root,
            descriptor_rel,
            classification=CLASS_STATUS,
            evidence_role="QMASTER_EXPORT_STATUS",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
        ),
        _artifact(
            root,
            csv_rel,
            classification=CLASS_BLOCKED,
            evidence_role="QMASTER_DERIVED_CURRENT_COMPOSITION_HISTORY",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
            extra={"csv_columns": columns, "csv_row_count": len(rows)},
        ),
        _artifact(
            root,
            alias_descriptor_rel,
            classification=CLASS_DUPLICATE,
            evidence_role="QMASTER_EXPORT_STATUS_ALIAS",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
            duplicate_of=descriptor_rel,
        ),
        _artifact(
            root,
            alias_csv_rel,
            classification=CLASS_DUPLICATE,
            evidence_role="QMASTER_DERIVED_HISTORY_ALIAS",
            scope="MULTIASSET_V2A",
            observed_or_derived="derived",
            duplicate_of=csv_rel,
        ),
    ]
    return artifacts, {
        "status": "BLOCKED_DERIVED_CURRENT_COMPOSITION_NOT_OFFICIAL_DATASET",
        "data_as_of": descriptor.get("data_as_of"),
        "rows": descriptor.get("rows"),
        "symbols": descriptor.get("symbols"),
        "duplicate_alias_count": 2,
        "canonical_path_auto_selected": False,
        "blockers": [
            "QMASTER_DERIVED_CURRENT_COMPOSITION_EXCLUDED",
            "QMASTER_SOURCE_ZIP_NOT_PHYSICALLY_PRESENT",
            "QMASTER_SOURCE_MANIFEST_NOT_PHYSICALLY_PRESENT",
            "QMASTER_V2A_INCOMPLETE_COVERAGE_PROPAGATED",
        ],
    }


def _validate_d50_status(root: Path, readiness: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    relative = "runtime/ledgers/d50/STATUS.json"
    status, _ = _load_json(root, relative)
    _require(status.get("schema") == "gate_btc.d50_measurement_status.v1", "D50 status schema mismatch")
    _verify_self_hash(status, "status_sha256", "D50 status")
    _verify_research_boundary(status, "D50 status")
    ledger = status.get("prospective_immutable_ledger")
    _require(isinstance(ledger, dict), "D50 prospective ledger status missing")
    source_hashes = ledger.get("source_hashes")
    _require(isinstance(source_hashes, dict), "D50 source hashes missing")
    _require(sorted(source_hashes) == ["funding", "ohlc"], "D50 source hash roles mismatch")
    for role, claimed in source_hashes.items():
        _require(HEX64.fullmatch(str(claimed)) is not None, f"D50 {role} source hash invalid")
    blockers = set(readiness["tracks"]["D50_ECONOMIC"].get("blockers", []))
    blockers.update(readiness["tracks"]["D50_QUALIFIED"].get("blockers", []))
    blockers.update(
        {
            "D50_FUNDING_SOURCE_BYTES_NOT_PHYSICALLY_PRESENT",
            "D50_OHLC_SOURCE_BYTES_NOT_PHYSICALLY_PRESENT",
            "D50_SOURCE_HASHES_HAVE_NO_RUNTIME_PATHS",
            "D50_SOURCE_PROVENANCE_NOT_BOUND",
            "D50_TABULAR_SCHEMA_NOT_BOUND",
        }
    )
    return [
        _artifact(
            root,
            relative,
            classification=CLASS_STATUS,
            evidence_role="D50_LEDGER_STATUS_WITH_HASH_ONLY_SOURCE_REFERENCES",
            scope="D50_ECONOMIC",
            observed_or_derived="derived",
            extra={"referenced_source_hashes": dict(sorted(source_hashes.items()))},
        )
    ], {
        "status": "BLOCKED_STATUS_AND_HASHES_WITHOUT_PHYSICAL_SOURCE_BYTES",
        "latest_prospective_date": ledger.get("latest_prospective_date"),
        "source_hashes": dict(sorted(source_hashes.items())),
        "source_paths_present": False,
        "blockers": sorted(blockers),
    }


def _utc_timestamp(value: str, label: str) -> datetime:
    _require(value.endswith("Z"), f"{label} timestamp is not explicit UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(f"invalid {label} timestamp: {value}") from exc
    _require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, f"{label} timestamp is not UTC")
    return parsed


def _validate_manual_market_data(
    root: Path,
    expected_cutoff: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        cutoff = date.fromisoformat(expected_cutoff)
    except ValueError as exc:
        raise RuntimeError(f"invalid evidence cutoff: {expected_cutoff}") from exc

    artifacts: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    required = {"timestamp", "open", "high", "low", "close", "volume", "symbol", "source"}
    for venue, spec in sorted(MANUAL_MARKET_SPECS.items()):
        for asset in ("BTC", "ETH", "SOL"):
            relative = spec["path"].format(asset=asset, asset_lower=asset.lower())
            columns, rows = _read_csv(root, relative)
            _require(required.issubset(columns), f"manual market columns missing: {relative}")
            _require("available_at_utc" not in columns, f"unexpected causal availability field requires contract review: {relative}")
            timestamps: list[datetime] = []
            incomplete_rows = 0
            for index, row in enumerate(rows, start=2):
                label = f"{relative}:{index}"
                timestamp = _utc_timestamp(str(row.get("timestamp", "")), label)
                timestamps.append(timestamp)
                _require(row.get("source") == spec["source"], f"manual market source mismatch: {label}")
                _require(row.get("symbol") == spec["symbol"].format(asset=asset), f"manual market symbol mismatch: {label}")
                _require(row.get(spec["interval_field"]) == spec["interval"], f"manual market interval mismatch: {label}")
                try:
                    open_value = float(row["open"])
                    high_value = float(row["high"])
                    low_value = float(row["low"])
                    close_value = float(row["close"])
                    volume_value = float(row["volume"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError(f"manual market numeric field invalid: {label}") from exc
                _require(
                    all(math.isfinite(value) for value in (open_value, high_value, low_value, close_value, volume_value)),
                    f"manual market non-finite value: {label}",
                )
                _require(high_value >= max(open_value, close_value), f"manual market OHLC high invariant: {label}")
                _require(low_value <= min(open_value, close_value), f"manual market OHLC low invariant: {label}")
                _require(low_value >= 0 and volume_value >= 0, f"manual market negative value: {label}")
                if "confirm" in row and row.get("confirm") != "1":
                    incomplete_rows += 1
            _require(timestamps == sorted(timestamps), f"manual market timestamps not sorted: {relative}")
            _require(len(timestamps) == len(set(timestamps)), f"manual market duplicate timestamps: {relative}")
            first = timestamps[0].isoformat().replace("+00:00", "Z") if timestamps else None
            last = timestamps[-1].isoformat().replace("+00:00", "Z") if timestamps else None
            latest_before_cutoff = not timestamps or timestamps[-1].date() < cutoff
            classification = CLASS_STALE if rows else CLASS_BLOCKED
            artifacts.append(
                _artifact(
                    root,
                    relative,
                    classification=classification,
                    evidence_role="MANUAL_PUBLIC_OHLC_CANDIDATE_NOT_OFFICIAL",
                    scope="BTC_CORE" if asset == "BTC" else "MULTIASSET_V2A",
                    observed_or_derived="observed",
                    extra={
                        "asset": asset,
                        "venue": venue,
                        "csv_columns": columns,
                        "csv_row_count": len(rows),
                        "first_observation_utc": first,
                        "last_observation_utc": last,
                        "latest_before_expected_cutoff": latest_before_cutoff,
                        "incomplete_row_count": incomplete_rows,
                        "available_at_utc_present": False,
                        "formal_schema_bound": False,
                        "source_provenance_bound": False,
                    },
                )
            )
            files.append(
                {
                    "asset": asset,
                    "venue": venue,
                    "path": relative,
                    "rows": len(rows),
                    "first_observation_utc": first,
                    "last_observation_utc": last,
                    "latest_before_expected_cutoff": latest_before_cutoff,
                    "incomplete_row_count": incomplete_rows,
                }
            )

    btc_files = [item for item in files if item["asset"] == "BTC"]
    _require(len(btc_files) == 4, "manual BTC market source set mismatch")
    nonempty_btc = [item for item in btc_files if item["rows"] > 0]
    empty_btc = [item["venue"] for item in btc_files if item["rows"] == 0]
    blockers = {
        "BTC_CORE_FUNDING_PARTITION_NOT_PHYSICALLY_PRESENT",
        "BTC_CORE_MANUAL_OHLC_AVAILABLE_AT_NOT_RECORDED",
        "BTC_CORE_MANUAL_OHLC_FORMAL_SCHEMA_NOT_BOUND",
        "BTC_CORE_MANUAL_OHLC_MULTISOURCE_MARKET_TYPE_MISMATCH",
        "BTC_CORE_MANUAL_OHLC_SOURCE_PROVENANCE_NOT_BOUND",
        "BTC_CORE_OFFICIAL_DESCRIPTOR_NOT_SUPPLIED",
    }
    if any(item["latest_before_expected_cutoff"] for item in btc_files):
        blockers.add("BTC_CORE_MANUAL_OHLC_LATEST_BEFORE_EXPECTED_CUTOFF")
    if empty_btc:
        blockers.add("BTC_CORE_MANUAL_OHLC_EMPTY_SOURCE_PRESENT")
    if any(item["incomplete_row_count"] for item in btc_files):
        blockers.add("BTC_CORE_MANUAL_OHLC_UNCONFIRMED_ROWS_PRESENT")
    return artifacts, {
        "status": "BLOCKED_STALE_UNSEALED_MANUAL_MARKET_EVIDENCE",
        "expected_cutoff": expected_cutoff,
        "file_count": len(files),
        "nonempty_file_count": sum(item["rows"] > 0 for item in files),
        "empty_file_count": sum(item["rows"] == 0 for item in files),
        "btc_nonempty_source_count": len(nonempty_btc),
        "btc_empty_sources": empty_btc,
        "files": sorted(files, key=lambda item: item["path"]),
        "blockers": sorted(blockers),
    }


def _discover_tabular(root: Path) -> dict[str, Any]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name.endswith(".partial"):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.endswith(TABULAR_SUFFIXES):
            _safe_file(root, rel)
            paths.append(rel)
    paths.sort()
    categories: dict[str, list[str]] = {
        "v2a_point_in_time_archives": [],
        "gateway_point_in_time_archives": [],
        "qmaster_aliases": [],
        "manual_public_market_data": [],
        "economic_research_inputs_excluded": [],
        "isolated_parallel_or_incumbent_ledgers": [],
        "unclassified": [],
    }
    for rel in paths:
        if V2A_ARCHIVE_RE.fullmatch(rel):
            categories["v2a_point_in_time_archives"].append(rel)
        elif GATEWAY_ARCHIVE_RE.fullmatch(rel):
            categories["gateway_point_in_time_archives"].append(rel)
        elif rel in QMASTER_PATHS:
            categories["qmaster_aliases"].append(rel)
        elif rel in MANUAL_MARKET_PATHS:
            categories["manual_public_market_data"].append(rel)
        elif rel in ECONOMIC_RESEARCH_INPUT_PATHS:
            categories["economic_research_inputs_excluded"].append(rel)
        elif rel.startswith(ISOLATED_TABULAR_PREFIXES):
            categories["isolated_parallel_or_incumbent_ledgers"].append(rel)
        else:
            categories["unclassified"].append(rel)
    return {
        "tabular_file_count": len(paths),
        "tabular_path_set_sha256": canonical_hash(paths),
        "category_counts": {name: len(values) for name, values in categories.items()},
        "unclassified_paths": categories["unclassified"],
        "economic_research_input_exclusions": categories["economic_research_inputs_excluded"],
        "isolated_exclusion_paths": categories["isolated_parallel_or_incumbent_ledgers"],
    }


def build_inventory(
    runtime_root: Path,
    runtime_commit: str,
    readiness: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Verify and classify current physical evidence without creating a seal."""
    _require(runtime_root.is_dir(), "runtime root is not a directory")
    _require(not runtime_root.is_symlink(), "runtime root must not be a symlink")
    _require(HEX40.fullmatch(runtime_commit) is not None, "runtime commit must be a lowercase 40-hex SHA")
    _require(validate_contract(contract) == [], "official dataset contract is invalid")
    _validate_readiness(readiness)

    v2a_artifacts, v2a = _validate_v2a(runtime_root, readiness)
    gateway_artifacts, gateway = _validate_gateway(runtime_root)
    qmaster_artifacts, qmaster = _validate_qmaster(runtime_root)
    d50_artifacts, d50 = _validate_d50_status(runtime_root, readiness)
    expected_cutoff = readiness.get("expected_cutoff")
    _require(isinstance(expected_cutoff, str), "readiness expected cutoff missing")
    manual_artifacts, manual_market = _validate_manual_market_data(runtime_root, expected_cutoff)
    artifacts = sorted(
        v2a_artifacts
        + gateway_artifacts
        + qmaster_artifacts
        + d50_artifacts
        + manual_artifacts,
        key=lambda item: item["path"],
    )
    tabular = _discover_tabular(runtime_root)

    btc_blockers = set(readiness["tracks"]["BTC_CORE"].get("blockers", []))
    btc_blockers.update(manual_market["blockers"])
    if tabular["unclassified_paths"]:
        btc_blockers.add("UNCLASSIFIED_TABULAR_EVIDENCE_PRESENT_FAIL_CLOSED")

    scope_assessments = {
        "BTC_CORE": {
            "status": "BLOCKED_NO_ADMISSIBLE_PHYSICAL_PARTITION",
            "admissible_candidate_count": 0,
            "blockers": sorted(btc_blockers),
        },
        "D50_ECONOMIC": {
            "status": d50["status"],
            "admissible_candidate_count": 0,
            "blockers": d50["blockers"],
        },
        "D50_QUALIFIED": {
            "status": d50["status"],
            "admissible_candidate_count": 0,
            "blockers": d50["blockers"],
        },
        "MULTIASSET_V2A": {
            "status": v2a["status"],
            "admissible_candidate_count": 0,
            "blockers": v2a["blockers"],
        },
    }
    all_blockers = {
        blocker
        for scope in scope_assessments.values()
        for blocker in scope["blockers"]
    }
    all_blockers.update(
        {
            "NO_ADMISSIBLE_OFFICIAL_DATASET_PARTITION",
            "OFFICIAL_DATASET_DESCRIPTOR_NOT_CREATED",
            "PARTIAL_SCOPE_SEAL_PROHIBITED",
        }
    )

    class_counts: dict[str, int] = {}
    for artifact in artifacts:
        classification = artifact["classification"]
        class_counts[classification] = class_counts.get(classification, 0) + 1

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "assessment_kind": ASSESSMENT_KIND,
        "status": STATUS,
        "runtime_commit": runtime_commit,
        "contract_sha256": contract["contract_sha256"],
        "readiness_assessment_sha256": readiness["assessment_sha256"],
        "readiness_status": readiness["status"],
        "expected_cutoff": readiness.get("expected_cutoff"),
        "physical_evidence": artifacts,
        "physical_evidence_count": len(artifacts),
        "classification_counts": dict(sorted(class_counts.items())),
        "admissible_candidate_count": 0,
        "duplicate_groups": [
            {
                "group_id": "QMASTER_RUNTIME_ALIAS",
                "canonical_path_auto_selected": False,
                "paths": [
                    "runtime/GATE_BTC_QMASTER_LATEST.csv",
                    "runtime/qmaster/GATE_BTC_QMASTER_LATEST.csv",
                ],
                "sha256": next(
                    item["sha256"]
                    for item in artifacts
                    if item["path"] == "runtime/GATE_BTC_QMASTER_LATEST.csv"
                ),
            },
            {
                "group_id": "QMASTER_STATUS_ALIAS",
                "canonical_path_auto_selected": False,
                "paths": [
                    "runtime/GATE_BTC_QMASTER_LATEST.txt",
                    "runtime/qmaster/GATE_BTC_QMASTER_LATEST.txt",
                ],
                "sha256": next(
                    item["sha256"]
                    for item in artifacts
                    if item["path"] == "runtime/GATE_BTC_QMASTER_LATEST.txt"
                ),
            },
        ],
        "scope_assessments": scope_assessments,
        "v2a_latest": v2a,
        "gateway_latest": gateway,
        "qmaster": qmaster,
        "d50": d50,
        "manual_market_evidence": manual_market,
        "tabular_discovery": tabular,
        "blockers": sorted(all_blockers),
        "safety": dict(SAFETY),
        "isolation": {
            "delta_mutations": 0,
            "regime_mutations": 0,
            "b3_mutations": 0,
            "incumbent_mutations": 0,
            "runtime_mutations": 0,
            "economic_families_released": 0,
        },
        "next_action": "RECOVER_GENUINE_BTC_D50_SOURCE_BYTES_AND_COMPLETE_V2A_THEN_AUTHOR_EXPLICIT_DESCRIPTOR_SCHEMA_AND_PROVENANCE",
    }
    payload["inventory_sha256"] = canonical_hash(payload)
    return payload


def _assert_safe_environment() -> None:
    expectations = {
        "GATE_BTC_RESEARCH_ONLY": "true",
        "GATE_BTC_SHADOW_ONLY": "true",
        "GATE_BTC_NOT_APPROVED": "true",
        "GATE_BTC_ENGINE_FEED": "false",
        "GATE_BTC_ORDERS": "0",
        "GATE_BTC_REAL_CAPITAL": "0",
    }
    for key, expected in expectations.items():
        _require(os.environ.get(key, expected).lower() == expected, f"unsafe environment field {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--runtime-commit", required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _assert_safe_environment()
    readiness = json.loads(args.readiness.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    payload = build_inventory(args.runtime_root, args.runtime_commit, readiness, contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "runtime_commit": payload["runtime_commit"],
                "physical_evidence_count": payload["physical_evidence_count"],
                "admissible_candidate_count": 0,
                "official_dataset_descriptor_created": False,
                "official_dataset_sealed": False,
                "official_challenger_runs_executed": 0,
                "orders_generated": 0,
                "real_capital_used": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
