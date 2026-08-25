#!/usr/bin/env python3
"""Fail-closed BTC_CORE/D50 source-admission adapter for GATE BTC 2.0.

This adapter validates exact OHLC and funding bytes, tabular schemas, source
provenance and causal availability.  A successful result is only ready for an
explicit source-admission review.  It does not admit or seal a dataset, credit
historical recovery as prospective evidence, run economics, feed an engine,
mutate a ledger, create orders or use capital.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "gate_btc.2_0.source_admission_contract.v1"
BUNDLE_SCHEMA = "gate_btc.2_0.source_admission_bundle.v1"
PROVENANCE_SCHEMA = "gate_btc.2_0.source_admission_provenance.v1"
TABULAR_SCHEMA = "gate_btc.2_0.tabular_dataset_schema.v1"
D50_STATUS_SCHEMA = "gate_btc.d50_measurement_status.v1"
EVIDENCE_INVENTORY_SCHEMA = "gate_btc.2_0.official_evidence_inventory.v1"
ADMISSION_SCHEMA = "gate_btc.2_0.source_admission_assessment.v1"
CURRENT_PREFLIGHT_SCHEMA = "gate_btc.2_0.current_source_admission_preflight.v1"

READY = "READY_FOR_EXPLICIT_SOURCE_ADMISSION_REVIEW"
BLOCKED = "BLOCKED_NOT_READY_FOR_SOURCE_ADMISSION_REVIEW"
CURRENT_BLOCKED = "BLOCKED_SOURCE_ADMISSION_NO_COMPLETE_BUNDLE"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

SCOPES = ["BTC_CORE", "D50_ECONOMIC", "D50_QUALIFIED"]
SOURCE_ROLES = ["FUNDING", "OHLC"]
FORMATS = ["csv", "jsonl"]
MARKET_TYPES = ["inverse_perpetual", "linear_perpetual", "spot"]
ACCESS_CLASSES = [
    "official_authenticated",
    "official_free",
    "official_free_fixture",
    "project_generated",
    "verified_public_mirror",
]
LICENSE_STATUSES = [
    "auditable_fixture",
    "project_generated",
    "verified_permitted",
]
AVAILABILITY_MODES = [
    "FILE_LEVEL_CONSERVATIVE_GIT_COMMIT",
    "ROW_LEVEL_PROVIDER_OR_VERIFIABLE_CAPTURE",
]
ROW_AVAILABILITY_EVIDENCE = {
    "PROVIDER_PUBLICATION_TIMESTAMP",
    "VERIFIABLE_CAPTURE_TIMESTAMP",
}

CONTRACT_SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
}

OUTPUT_SAFETY = {
    **CONTRACT_SAFETY,
    "source_admitted": False,
    "official_dataset_descriptor_created": False,
    "official_dataset_sealed": False,
    "official_challenger_runs_executed": 0,
    "economic_calibration_performed": False,
    "canonical_data_writes": 0,
    "prospective_rows_credited": 0,
    "historical_rows_backfilled": 0,
    "ledger_mutations": 0,
    "incumbent_mutations": 0,
}

CURRENT_INVENTORY_SAFETY = {
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

EXPECTED_POLICIES = {
    "admission_requires_explicit_review": True,
    "canonical_dataset_write_allowed": False,
    "economic_calibration_allowed": False,
    "file_level_git_commit_is_conservative_availability": True,
    "funding_inferred_from_ohlc_allowed": False,
    "mixed_market_partition_allowed": False,
    "official_dataset_seal_allowed": False,
    "partial_role_admission_allowed": False,
    "provider_availability_may_be_invented": False,
    "recovered_historical_counts_as_prospective": False,
    "retrospective_backfill_allowed": False,
    "unconfirmed_rows_allowed": False,
}

EXPECTED_PROSPECTIVE_CREDIT = {
    "frozen_ledger_mutations": 0,
    "historical_rows_credited": 0,
    "recovered_historical_rows_credited": 0,
    "source_admission_counter_increments": 0,
}

DESCRIPTOR_FIELDS = [
    "schema",
    "bundle_id",
    "bundle_version",
    "baseline_commit_sha",
    "created_at_utc",
    "cutoff_utc",
    "assessment_at_utc",
    "contract_sha256",
    "scopes",
    "d50_claimed_source_hashes",
    "sources",
    "partitions",
    "prospective_credit",
    "policies",
    "safety",
]

SOURCE_FIELDS = [
    "source_id",
    "source_role",
    "provider",
    "venue",
    "market_type",
    "instrument",
    "normalized_asset",
    "source_reference",
    "access_class",
    "license_status",
    "observed_or_derived",
    "timezone",
    "causal_availability_rule",
    "immutable_reference",
    "availability_evidence_type",
    "availability_evidence_reference",
    "provenance_path",
    "expected_provenance_sha256",
]

PROVENANCE_FIELDS = [
    "schema",
    "source_id",
    "source_role",
    "provider",
    "venue",
    "market_type",
    "instrument",
    "normalized_asset",
    "source_reference",
    "access_class",
    "license_status",
    "observed_or_derived",
    "timezone",
    "causal_availability_rule",
    "immutable_reference",
    "availability_evidence_type",
    "availability_evidence_reference",
    "retrieved_at_utc",
    "retrieval_method",
    "original_filename",
    "content_sha256",
]

PARTITION_FIELDS = [
    "partition_id",
    "source_id",
    "source_role",
    "relative_path",
    "schema_path",
    "format",
    "granularity",
    "expected_sha256",
    "expected_schema_sha256",
    "availability_mode",
    "file_available_at_utc",
    "row_count",
    "first_observation_utc",
    "last_observation_utc",
    "contains_unconfirmed_rows",
    "recovered_historical",
]

ROLE_REQUIREMENTS = {
    "OHLC": {
        "identifier",
        "observation_timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    },
    "FUNDING": {"identifier", "observation_timestamp", "funding_rate"},
}

ROLE_ALLOWED = {
    "OHLC": ROLE_REQUIREMENTS["OHLC"] | {"available_at", "confirmation"},
    "FUNDING": ROLE_REQUIREMENTS["FUNDING"] | {"available_at", "confirmation"},
}


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _required(payload: Any, fields: list[str], prefix: str, errors: list[str]) -> bool:
    if not isinstance(payload, dict):
        errors.append(f"{prefix}_NOT_OBJECT")
        return False
    missing = [field for field in fields if field not in payload]
    errors.extend(f"{prefix}_MISSING_{field.upper()}" for field in missing)
    return not missing


def _utc(value: Any, code: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(code)
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(code)
        return None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        errors.append(code)
        return None
    return parsed


def _safe_file(root: Path, relative: Any, code: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        errors.append(code)
        return None
    try:
        root_resolved = root.resolve(strict=True)
        candidate = root / relative
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (FileNotFoundError, OSError, ValueError):
        errors.append(code)
        return None
    if candidate.is_symlink() or not resolved.is_file():
        errors.append(code)
        return None
    current = candidate.parent
    while current != root and current != current.parent:
        if current.is_symlink():
            errors.append(code)
            return None
        current = current.parent
    return resolved


def _load_json_file(path: Path, code: str, errors: list[str]) -> tuple[dict[str, Any], bytes] | None:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(code)
        return None
    if not isinstance(payload, dict):
        errors.append(code)
        return None
    return payload, raw


def _verify_self_hash(payload: dict[str, Any], field: str, code: str, errors: list[str]) -> None:
    unsigned = dict(payload)
    claimed = unsigned.pop(field, None)
    if not HEX64.fullmatch(str(claimed)) or claimed != canonical_hash(unsigned):
        errors.append(code)


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("CONTRACT_SCHEMA_INVALID")
    if contract.get("contract_version") != 1:
        errors.append("CONTRACT_VERSION_INVALID")
    if contract.get("status") != "FROZEN_DATA_READINESS_ONLY":
        errors.append("CONTRACT_STATUS_INVALID")
    if contract.get("parent_dataset_contract_sha256") != "b57281c6eb9850d45bfff96ff52bdabb4942e3e6dff404e5745ac7e3af26381b":
        errors.append("CONTRACT_PARENT_INVALID")
    if contract.get("admission_scopes") != SCOPES:
        errors.append("CONTRACT_SCOPES_INVALID")
    if contract.get("required_source_roles") != SOURCE_ROLES:
        errors.append("CONTRACT_SOURCE_ROLES_INVALID")
    if contract.get("allowed_formats") != FORMATS:
        errors.append("CONTRACT_FORMATS_INVALID")
    if contract.get("allowed_market_types") != MARKET_TYPES:
        errors.append("CONTRACT_MARKET_TYPES_INVALID")
    if contract.get("allowed_access_classes") != ACCESS_CLASSES:
        errors.append("CONTRACT_ACCESS_CLASSES_INVALID")
    if contract.get("allowed_license_statuses") != LICENSE_STATUSES:
        errors.append("CONTRACT_LICENSE_STATUSES_INVALID")
    if contract.get("availability_modes") != AVAILABILITY_MODES:
        errors.append("CONTRACT_AVAILABILITY_MODES_INVALID")
    if contract.get("descriptor_required_fields") != DESCRIPTOR_FIELDS:
        errors.append("CONTRACT_DESCRIPTOR_FIELDS_INVALID")
    if contract.get("source_required_fields") != SOURCE_FIELDS:
        errors.append("CONTRACT_SOURCE_FIELDS_INVALID")
    if contract.get("provenance_required_fields") != PROVENANCE_FIELDS:
        errors.append("CONTRACT_PROVENANCE_FIELDS_INVALID")
    if contract.get("partition_required_fields") != PARTITION_FIELDS:
        errors.append("CONTRACT_PARTITION_FIELDS_INVALID")
    if contract.get("source_provenance_schema") != PROVENANCE_SCHEMA:
        errors.append("CONTRACT_PROVENANCE_SCHEMA_INVALID")
    if contract.get("tabular_schema") != TABULAR_SCHEMA:
        errors.append("CONTRACT_TABULAR_SCHEMA_INVALID")
    if contract.get("policies") != EXPECTED_POLICIES:
        errors.append("CONTRACT_POLICIES_INVALID")
    if contract.get("safety") != CONTRACT_SAFETY:
        errors.append("CONTRACT_SAFETY_INVALID")
    expected_roles = {key: sorted(value) for key, value in ROLE_REQUIREMENTS.items()}
    if contract.get("required_column_roles") != expected_roles:
        errors.append("CONTRACT_COLUMN_ROLES_INVALID")
    unsigned = dict(contract)
    claimed = unsigned.pop("contract_sha256", None)
    if not HEX64.fullmatch(str(claimed)) or claimed != canonical_hash(unsigned):
        errors.append("CONTRACT_HASH_INVALID")
    return sorted(set(errors))


def _parse_rows(
    raw: bytes,
    fmt: str,
    columns: list[str],
    partition_id: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        errors.append(f"PARTITION_{partition_id}_NOT_UTF8")
        return []
    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(text, newline=""))
        fieldnames = reader.fieldnames or []
        if fieldnames != columns or len(fieldnames) != len(set(fieldnames)):
            errors.append(f"PARTITION_{partition_id}_COLUMN_SCHEMA_MISMATCH")
        rows = list(reader)
        if any(None in row or set(row) != set(columns) for row in rows):
            errors.append(f"PARTITION_{partition_id}_COLUMN_SCHEMA_MISMATCH")
    elif fmt == "jsonl":
        rows = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"PARTITION_{partition_id}_JSONL_INVALID_ROW_{line_number}")
                continue
            if not isinstance(row, dict):
                errors.append(f"PARTITION_{partition_id}_ROW_NOT_OBJECT_{line_number}")
                continue
            if set(row) != set(columns):
                errors.append(f"PARTITION_{partition_id}_COLUMN_SCHEMA_MISMATCH")
            rows.append(row)
    else:
        errors.append(f"PARTITION_{partition_id}_FORMAT_INVALID")
        return []
    if not rows:
        errors.append(f"PARTITION_{partition_id}_EMPTY")
    return rows


def _validate_schema(
    schema: dict[str, Any],
    source_role: str,
    fmt: str,
    availability_mode: str,
    partition_id: str,
    errors: list[str],
) -> tuple[list[str], dict[str, str], list[str]]:
    prefix = f"SCHEMA_{partition_id}"
    required_fields = [
        "schema",
        "schema_id",
        "format",
        "timezone",
        "columns",
        "primary_key",
        "economic_fields",
        "future_known_metadata_allowed",
    ]
    if not _required(schema, required_fields, prefix, errors):
        return [], {}, []
    if schema.get("schema") != TABULAR_SCHEMA:
        errors.append(f"{prefix}_IDENTIFIER_INVALID")
    if schema.get("format") != fmt:
        errors.append(f"{prefix}_FORMAT_MISMATCH")
    if schema.get("timezone") != "UTC":
        errors.append(f"{prefix}_TIMEZONE_NOT_UTC")
    if schema.get("economic_fields") != []:
        errors.append(f"{prefix}_ECONOMIC_FIELDS_FORBIDDEN")
    if schema.get("future_known_metadata_allowed") is not False:
        errors.append(f"{prefix}_FUTURE_METADATA_UNSAFE")
    columns_payload = schema.get("columns")
    if not isinstance(columns_payload, list) or not columns_payload:
        errors.append(f"{prefix}_COLUMNS_INVALID")
        return [], {}, []
    columns: list[str] = []
    role_to_names: dict[str, list[str]] = {}
    for index, column in enumerate(columns_payload):
        column_prefix = f"{prefix}_COLUMN_{index}"
        if not _required(column, ["name", "type", "role"], column_prefix, errors):
            continue
        name = column.get("name")
        role = column.get("role")
        if not isinstance(name, str) or not name:
            errors.append(f"{column_prefix}_NAME_INVALID")
            continue
        if not isinstance(column.get("type"), str) or not column.get("type"):
            errors.append(f"{column_prefix}_TYPE_INVALID")
        if not isinstance(role, str) or not role:
            errors.append(f"{column_prefix}_ROLE_INVALID")
            continue
        columns.append(name)
        role_to_names.setdefault(role, []).append(name)
    if len(columns) != len(set(columns)):
        errors.append(f"{prefix}_DUPLICATE_COLUMNS")
    for role, names in role_to_names.items():
        if role not in ROLE_ALLOWED.get(source_role, set()):
            errors.append(f"{prefix}_ROLE_FORBIDDEN:{role}")
        if len(names) != 1:
            errors.append(f"{prefix}_ROLE_DUPLICATED:{role}")
    for required_role in ROLE_REQUIREMENTS.get(source_role, set()):
        if len(role_to_names.get(required_role, [])) != 1:
            errors.append(f"{prefix}_ROLE_REQUIRED:{required_role}")
    available_count = len(role_to_names.get("available_at", []))
    if availability_mode == "ROW_LEVEL_PROVIDER_OR_VERIFIABLE_CAPTURE" and available_count != 1:
        errors.append(f"{prefix}_ROW_AVAILABLE_AT_REQUIRED")
    if availability_mode == "FILE_LEVEL_CONSERVATIVE_GIT_COMMIT" and available_count != 0:
        errors.append(f"{prefix}_FILE_MODE_ROW_AVAILABLE_AT_FORBIDDEN")
    primary_key = schema.get("primary_key")
    if not isinstance(primary_key, list) or any(field not in columns for field in primary_key):
        errors.append(f"{prefix}_PRIMARY_KEY_INVALID")
        primary_key = []
    required_pk = {
        role_to_names.get("identifier", [None])[0],
        role_to_names.get("observation_timestamp", [None])[0],
    }
    required_pk.discard(None)
    if not required_pk.issubset(set(primary_key)):
        errors.append(f"{prefix}_PRIMARY_KEY_MISSING_CAUSAL_IDENTITY")
    single_roles = {
        role: names[0]
        for role, names in role_to_names.items()
        if len(names) == 1
    }
    return columns, single_roles, primary_key


def _finite_number(value: Any, code: str, errors: list[str]) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        errors.append(code)
        return None
    if not math.isfinite(result):
        errors.append(code)
        return None
    return result


def _confirmation(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "confirmed"}


def _validate_d50_status(status: dict[str, Any], errors: list[str]) -> dict[str, str]:
    if status.get("schema") != D50_STATUS_SCHEMA:
        errors.append("D50_STATUS_SCHEMA_INVALID")
    _verify_self_hash(status, "status_sha256", "D50_STATUS_HASH_INVALID", errors)
    for key, expected in {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }.items():
        if status.get(key) != expected:
            errors.append(f"D50_STATUS_SAFETY_{key.upper()}")
    ledger = status.get("prospective_immutable_ledger")
    if not isinstance(ledger, dict):
        errors.append("D50_STATUS_LEDGER_INVALID")
        return {}
    hashes = ledger.get("source_hashes")
    if not isinstance(hashes, dict) or sorted(hashes) != ["funding", "ohlc"]:
        errors.append("D50_STATUS_SOURCE_HASHES_INVALID")
        return {}
    for role, claimed in hashes.items():
        if not HEX64.fullmatch(str(claimed)):
            errors.append(f"D50_STATUS_{role.upper()}_HASH_INVALID")
    if ledger.get("historical_backfill_counts_as_prospective") is not False:
        errors.append("D50_STATUS_HISTORICAL_BACKFILL_POLICY_UNSAFE")
    if ledger.get("mutation_performed") is not False:
        errors.append("D50_STATUS_LEDGER_MUTATION_REPORTED")
    return {key.upper(): str(value) for key, value in hashes.items()}


def build_source_admission(
    bundle_root: Path,
    descriptor: dict[str, Any],
    d50_status: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate an exact source bundle without admitting it or mutating state."""
    contract_errors = validate_contract(contract)
    if contract_errors:
        raise RuntimeError("invalid frozen source admission contract: " + "; ".join(contract_errors))
    errors: list[str] = []
    if not bundle_root.is_dir() or bundle_root.is_symlink():
        errors.append("BUNDLE_ROOT_INVALID")

    complete_descriptor = _required(descriptor, DESCRIPTOR_FIELDS, "BUNDLE", errors)
    if descriptor.get("schema") != BUNDLE_SCHEMA:
        errors.append("BUNDLE_SCHEMA_INVALID")
    if descriptor.get("contract_sha256") != contract.get("contract_sha256"):
        errors.append("BUNDLE_CONTRACT_HASH_MISMATCH")
    if descriptor.get("scopes") != SCOPES:
        errors.append("BUNDLE_SCOPES_INVALID")
    if descriptor.get("policies") != EXPECTED_POLICIES:
        errors.append("BUNDLE_POLICIES_MISMATCH")
    if descriptor.get("safety") != CONTRACT_SAFETY:
        errors.append("BUNDLE_SAFETY_MISMATCH")
    if descriptor.get("prospective_credit") != EXPECTED_PROSPECTIVE_CREDIT:
        errors.append("BUNDLE_PROSPECTIVE_CREDIT_UNSAFE")
    if not HEX40.fullmatch(str(descriptor.get("baseline_commit_sha"))):
        errors.append("BUNDLE_BASELINE_COMMIT_INVALID")
    for field in ("bundle_id", "bundle_version"):
        if not isinstance(descriptor.get(field), str) or not descriptor.get(field):
            errors.append(f"BUNDLE_{field.upper()}_INVALID")
    created = _utc(descriptor.get("created_at_utc"), "BUNDLE_CREATED_AT_INVALID", errors)
    cutoff = _utc(descriptor.get("cutoff_utc"), "BUNDLE_CUTOFF_INVALID", errors)
    assessment = _utc(descriptor.get("assessment_at_utc"), "BUNDLE_ASSESSMENT_AT_INVALID", errors)
    if cutoff and assessment and cutoff > assessment:
        errors.append("BUNDLE_CUTOFF_AFTER_ASSESSMENT")
    if created and assessment and created > assessment:
        errors.append("BUNDLE_CREATED_AFTER_ASSESSMENT")

    status_hashes = _validate_d50_status(d50_status, errors)
    claims = descriptor.get("d50_claimed_source_hashes")
    if not isinstance(claims, dict) or sorted(claims) != SOURCE_ROLES:
        errors.append("BUNDLE_D50_CLAIMED_HASHES_INVALID")
        claims = {}
    for role in SOURCE_ROLES:
        claimed = claims.get(role)
        if not HEX64.fullmatch(str(claimed)):
            errors.append(f"BUNDLE_D50_{role}_HASH_INVALID")
        if claimed != status_hashes.get(role):
            errors.append(f"BUNDLE_D50_{role}_STATUS_HASH_MISMATCH")

    sources_payload = descriptor.get("sources")
    if not isinstance(sources_payload, list):
        errors.append("BUNDLE_SOURCES_INVALID")
        sources_payload = []
    partitions_payload = descriptor.get("partitions")
    if not isinstance(partitions_payload, list):
        errors.append("BUNDLE_PARTITIONS_INVALID")
        partitions_payload = []
    if len(sources_payload) != 2:
        errors.append("BUNDLE_EXACTLY_TWO_SOURCES_REQUIRED")
    if len(partitions_payload) != 2:
        errors.append("BUNDLE_EXACTLY_TWO_PARTITIONS_REQUIRED")

    sources: dict[str, dict[str, Any]] = {}
    source_roles: list[str] = []
    source_market_identities: set[tuple[Any, Any, Any]] = set()
    provenance_by_source: dict[str, dict[str, Any]] = {}
    file_inventory: list[dict[str, Any]] = []
    for index, source in enumerate(sources_payload):
        prefix = f"SOURCE_{index}"
        if not _required(source, SOURCE_FIELDS, prefix, errors):
            continue
        source_id = source.get("source_id")
        source_role = source.get("source_role")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}_ID_INVALID")
            continue
        if source_id in sources:
            errors.append(f"SOURCE_ID_DUPLICATE:{source_id}")
            continue
        if source_role not in SOURCE_ROLES:
            errors.append(f"SOURCE_{source_id}_ROLE_INVALID")
        else:
            source_roles.append(source_role)
        sources[source_id] = source
        for field in (
            "provider",
            "venue",
            "instrument",
            "source_reference",
            "access_class",
            "license_status",
            "causal_availability_rule",
            "availability_evidence_type",
            "availability_evidence_reference",
        ):
            if not isinstance(source.get(field), str) or not source.get(field):
                errors.append(f"SOURCE_{source_id}_{field.upper()}_INVALID")
        if source.get("market_type") not in MARKET_TYPES:
            errors.append(f"SOURCE_{source_id}_MARKET_TYPE_INVALID")
        if source.get("access_class") not in ACCESS_CLASSES:
            errors.append(f"SOURCE_{source_id}_ACCESS_CLASS_INVALID")
        if source.get("license_status") not in LICENSE_STATUSES:
            errors.append(f"SOURCE_{source_id}_LICENSE_STATUS_INVALID")
        if source.get("normalized_asset") != "BTC":
            errors.append(f"SOURCE_{source_id}_ASSET_NOT_BTC")
        if source.get("observed_or_derived") != "observed":
            errors.append(f"SOURCE_{source_id}_NOT_OBSERVED")
        if source.get("timezone") != "UTC":
            errors.append(f"SOURCE_{source_id}_TIMEZONE_NOT_UTC")
        if source.get("immutable_reference") is not True:
            errors.append(f"SOURCE_{source_id}_REFERENCE_NOT_IMMUTABLE")
        source_market_identities.add(
            (source.get("venue"), source.get("market_type"), source.get("instrument"))
        )
        expected_provenance = source.get("expected_provenance_sha256")
        if not HEX64.fullmatch(str(expected_provenance)):
            errors.append(f"SOURCE_{source_id}_PROVENANCE_HASH_INVALID")
        provenance_path = _safe_file(
            bundle_root,
            source.get("provenance_path"),
            f"SOURCE_{source_id}_PROVENANCE_PATH_INVALID",
            errors,
        )
        if provenance_path is None:
            continue
        loaded = _load_json_file(
            provenance_path,
            f"SOURCE_{source_id}_PROVENANCE_JSON_INVALID",
            errors,
        )
        if loaded is None:
            continue
        provenance, provenance_raw = loaded
        observed_hash = _sha256(provenance_raw)
        if observed_hash != expected_provenance:
            errors.append(f"SOURCE_{source_id}_PROVENANCE_HASH_MISMATCH")
        if not _required(provenance, PROVENANCE_FIELDS, f"SOURCE_{source_id}_PROVENANCE", errors):
            continue
        if provenance.get("schema") != PROVENANCE_SCHEMA:
            errors.append(f"SOURCE_{source_id}_PROVENANCE_SCHEMA_INVALID")
        for field in SOURCE_FIELDS:
            if field in {"provenance_path", "expected_provenance_sha256"}:
                continue
            if provenance.get(field) != source.get(field):
                errors.append(f"SOURCE_{source_id}_PROVENANCE_FIELD_MISMATCH:{field}")
        retrieved = _utc(
            provenance.get("retrieved_at_utc"),
            f"SOURCE_{source_id}_PROVENANCE_RETRIEVED_AT_INVALID",
            errors,
        )
        if retrieved and assessment and retrieved > assessment:
            errors.append(f"SOURCE_{source_id}_PROVENANCE_RETRIEVED_AFTER_ASSESSMENT")
        for field in ("retrieval_method", "original_filename"):
            if not isinstance(provenance.get(field), str) or not provenance.get(field):
                errors.append(f"SOURCE_{source_id}_PROVENANCE_{field.upper()}_INVALID")
        if not HEX64.fullmatch(str(provenance.get("content_sha256"))):
            errors.append(f"SOURCE_{source_id}_PROVENANCE_CONTENT_HASH_INVALID")
        provenance_by_source[source_id] = provenance
        file_inventory.append(
            {
                "kind": "SOURCE_PROVENANCE",
                "path": source["provenance_path"],
                "sha256": observed_hash,
                "byte_length": len(provenance_raw),
                "source_id": source_id,
            }
        )
    if sorted(source_roles) != SOURCE_ROLES:
        errors.append("BUNDLE_SOURCE_ROLE_COVERAGE_INVALID")
    if len(source_market_identities) != 1:
        errors.append("BUNDLE_CROSS_ROLE_MARKET_IDENTITY_MISMATCH")

    partition_roles: list[str] = []
    seen_partition_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    partition_summaries: list[dict[str, Any]] = []
    recovered_count = 0
    for index, partition in enumerate(partitions_payload):
        prefix = f"PARTITION_{index}"
        if not _required(partition, PARTITION_FIELDS, prefix, errors):
            continue
        partition_id = partition.get("partition_id")
        if not isinstance(partition_id, str) or not partition_id:
            errors.append(f"{prefix}_ID_INVALID")
            continue
        if partition_id in seen_partition_ids:
            errors.append(f"PARTITION_ID_DUPLICATE:{partition_id}")
            continue
        seen_partition_ids.add(partition_id)
        source_id = partition.get("source_id")
        source_role = partition.get("source_role")
        source = sources.get(source_id)
        if source is None:
            errors.append(f"PARTITION_{partition_id}_SOURCE_UNKNOWN")
        else:
            if source_id in seen_source_ids:
                errors.append(f"PARTITION_{partition_id}_SOURCE_REUSED_MIXED_PARTITION")
            seen_source_ids.add(source_id)
            if source.get("source_role") != source_role:
                errors.append(f"PARTITION_{partition_id}_SOURCE_ROLE_MISMATCH")
        if source_role not in SOURCE_ROLES:
            errors.append(f"PARTITION_{partition_id}_ROLE_INVALID")
        else:
            partition_roles.append(source_role)
        fmt = partition.get("format")
        if fmt not in FORMATS:
            errors.append(f"PARTITION_{partition_id}_FORMAT_INVALID")
        availability_mode = partition.get("availability_mode")
        if availability_mode not in AVAILABILITY_MODES:
            errors.append(f"PARTITION_{partition_id}_AVAILABILITY_MODE_INVALID")
        if partition.get("contains_unconfirmed_rows") is not False:
            errors.append(f"PARTITION_{partition_id}_UNCONFIRMED_ROWS_DECLARED")
        recovered = partition.get("recovered_historical")
        if not isinstance(recovered, bool):
            errors.append(f"PARTITION_{partition_id}_RECOVERY_FLAG_INVALID")
        elif recovered:
            recovered_count += 1
        expected_data_hash = partition.get("expected_sha256")
        expected_schema_hash = partition.get("expected_schema_sha256")
        if not HEX64.fullmatch(str(expected_data_hash)):
            errors.append(f"PARTITION_{partition_id}_DATA_HASH_INVALID")
        if not HEX64.fullmatch(str(expected_schema_hash)):
            errors.append(f"PARTITION_{partition_id}_SCHEMA_HASH_INVALID")
        if expected_data_hash != claims.get(source_role):
            errors.append(f"PARTITION_{partition_id}_D50_HASH_MISMATCH")

        data_path = _safe_file(
            bundle_root,
            partition.get("relative_path"),
            f"PARTITION_{partition_id}_DATA_PATH_INVALID",
            errors,
        )
        schema_path = _safe_file(
            bundle_root,
            partition.get("schema_path"),
            f"PARTITION_{partition_id}_SCHEMA_PATH_INVALID",
            errors,
        )
        if data_path is None or schema_path is None:
            continue
        data_raw = data_path.read_bytes()
        if _sha256(data_raw) != expected_data_hash:
            errors.append(f"PARTITION_{partition_id}_DATA_HASH_MISMATCH")
        loaded_schema = _load_json_file(
            schema_path,
            f"PARTITION_{partition_id}_SCHEMA_JSON_INVALID",
            errors,
        )
        if loaded_schema is None:
            continue
        schema, schema_raw = loaded_schema
        if _sha256(schema_raw) != expected_schema_hash:
            errors.append(f"PARTITION_{partition_id}_SCHEMA_HASH_MISMATCH")
        columns, roles, primary_key = _validate_schema(
            schema,
            str(source_role),
            str(fmt),
            str(availability_mode),
            partition_id,
            errors,
        )
        rows = _parse_rows(data_raw, str(fmt), columns, partition_id, errors)
        observations: list[datetime] = []
        primary_keys: set[tuple[str, ...]] = set()
        file_available: datetime | None = None
        if availability_mode == "FILE_LEVEL_CONSERVATIVE_GIT_COMMIT":
            file_available = _utc(
                partition.get("file_available_at_utc"),
                f"PARTITION_{partition_id}_FILE_AVAILABLE_AT_INVALID",
                errors,
            )
            if source and source.get("availability_evidence_type") != "FIRST_REPOSITORY_COMMIT_TIMESTAMP":
                errors.append(f"PARTITION_{partition_id}_GIT_AVAILABILITY_EVIDENCE_INVALID")
            if source and not HEX40.fullmatch(str(source.get("availability_evidence_reference"))):
                errors.append(f"PARTITION_{partition_id}_GIT_AVAILABILITY_COMMIT_INVALID")
            if cutoff and file_available and file_available > cutoff:
                errors.append(f"PARTITION_{partition_id}_FILE_AVAILABLE_AFTER_CUTOFF")
            if created and file_available and file_available > created:
                errors.append(f"PARTITION_{partition_id}_FILE_AVAILABLE_AFTER_BUNDLE_CREATION")
            provenance = provenance_by_source.get(str(source_id))
            if provenance and file_available:
                retrieved = _utc(
                    provenance.get("retrieved_at_utc"),
                    f"PARTITION_{partition_id}_PROVENANCE_RETRIEVED_AT_INVALID",
                    errors,
                )
                if retrieved and retrieved < file_available:
                    errors.append(f"PARTITION_{partition_id}_RETRIEVED_BEFORE_FILE_AVAILABILITY")
        elif availability_mode == "ROW_LEVEL_PROVIDER_OR_VERIFIABLE_CAPTURE":
            if partition.get("file_available_at_utc") is not None:
                errors.append(f"PARTITION_{partition_id}_ROW_MODE_FILE_AVAILABLE_AT_FORBIDDEN")
            if source and source.get("availability_evidence_type") not in ROW_AVAILABILITY_EVIDENCE:
                errors.append(f"PARTITION_{partition_id}_ROW_AVAILABILITY_EVIDENCE_INVALID")

        identifier_name = roles.get("identifier")
        observation_name = roles.get("observation_timestamp")
        available_name = roles.get("available_at")
        confirmation_name = roles.get("confirmation")
        unconfirmed_count = 0
        for row_number, row in enumerate(rows, start=1):
            code = f"PARTITION_{partition_id}_ROW_{row_number}"
            observation = _utc(row.get(observation_name), f"{code}_OBSERVATION_TIMESTAMP_INVALID", errors)
            if observation is not None:
                observations.append(observation)
                if cutoff and observation > cutoff:
                    errors.append(f"{code}_OBSERVATION_AFTER_CUTOFF")
                if file_available and observation > file_available:
                    errors.append(f"{code}_OBSERVATION_AFTER_FILE_AVAILABILITY")
            if identifier_name and source and row.get(identifier_name) != source.get("instrument"):
                errors.append(f"{code}_INSTRUMENT_MISMATCH")
            if available_name:
                available = _utc(row.get(available_name), f"{code}_AVAILABLE_AT_INVALID", errors)
                if observation and available and available < observation:
                    errors.append(f"{code}_AVAILABLE_BEFORE_OBSERVATION")
                if cutoff and available and available > cutoff:
                    errors.append(f"{code}_AVAILABLE_AFTER_CUTOFF")
            if confirmation_name and not _confirmation(row.get(confirmation_name)):
                unconfirmed_count += 1
                errors.append(f"{code}_UNCONFIRMED")
            key = tuple(str(row.get(field)) for field in primary_key)
            if key in primary_keys:
                errors.append(f"{code}_DUPLICATE_PRIMARY_KEY")
            primary_keys.add(key)
            if source_role == "OHLC":
                values = {
                    role: _finite_number(row.get(roles.get(role)), f"{code}_{role.upper()}_INVALID", errors)
                    for role in ("open", "high", "low", "close", "volume")
                }
                if all(value is not None for value in values.values()):
                    if values["low"] < 0 or values["volume"] < 0:
                        errors.append(f"{code}_NEGATIVE_OHLC_OR_VOLUME")
                    if values["high"] < max(values["open"], values["close"]):
                        errors.append(f"{code}_OHLC_HIGH_INVARIANT")
                    if values["low"] > min(values["open"], values["close"]):
                        errors.append(f"{code}_OHLC_LOW_INVARIANT")
            elif source_role == "FUNDING":
                rate = _finite_number(
                    row.get(roles.get("funding_rate")),
                    f"{code}_FUNDING_RATE_INVALID",
                    errors,
                )
                if rate is not None and not -1 <= rate <= 1:
                    errors.append(f"{code}_FUNDING_RATE_OUT_OF_RANGE")
        if observations != sorted(observations):
            errors.append(f"PARTITION_{partition_id}_OBSERVATIONS_NOT_SORTED")
        first = observations[0].isoformat().replace("+00:00", "Z") if observations else None
        last = observations[-1].isoformat().replace("+00:00", "Z") if observations else None
        if partition.get("row_count") != len(rows):
            errors.append(f"PARTITION_{partition_id}_ROW_COUNT_MISMATCH")
        if partition.get("first_observation_utc") != first:
            errors.append(f"PARTITION_{partition_id}_FIRST_OBSERVATION_MISMATCH")
        if partition.get("last_observation_utc") != last:
            errors.append(f"PARTITION_{partition_id}_LAST_OBSERVATION_MISMATCH")
        if unconfirmed_count and partition.get("contains_unconfirmed_rows") is False:
            errors.append(f"PARTITION_{partition_id}_UNCONFIRMED_DISCLOSURE_MISMATCH")
        provenance = provenance_by_source.get(str(source_id))
        if provenance and provenance.get("content_sha256") != expected_data_hash:
            errors.append(f"PARTITION_{partition_id}_PROVENANCE_CONTENT_HASH_MISMATCH")
        file_inventory.extend(
            [
                {
                    "kind": source_role,
                    "path": partition["relative_path"],
                    "sha256": _sha256(data_raw),
                    "byte_length": len(data_raw),
                    "source_id": source_id,
                    "partition_id": partition_id,
                    "row_count": len(rows),
                },
                {
                    "kind": "TABULAR_SCHEMA",
                    "path": partition["schema_path"],
                    "sha256": _sha256(schema_raw),
                    "byte_length": len(schema_raw),
                    "source_id": source_id,
                    "partition_id": partition_id,
                },
            ]
        )
        partition_summaries.append(
            {
                "partition_id": partition_id,
                "source_id": source_id,
                "source_role": source_role,
                "availability_mode": availability_mode,
                "row_count": len(rows),
                "first_observation_utc": first,
                "last_observation_utc": last,
                "recovered_historical": recovered,
                "prospective_rows_credited": 0,
            }
        )
    if sorted(partition_roles) != SOURCE_ROLES:
        errors.append("BUNDLE_PARTITION_ROLE_COVERAGE_INVALID")
    if set(sources) != seen_source_ids:
        errors.append("BUNDLE_SOURCE_PARTITION_BINDING_INCOMPLETE")
    if complete_descriptor is False:
        errors.append("BUNDLE_DESCRIPTOR_INCOMPLETE")

    blockers = sorted(set(errors))
    payload: dict[str, Any] = {
        "schema": ADMISSION_SCHEMA,
        "assessment_kind": "SOURCE_ADMISSION_REVIEW_PREFLIGHT_ONLY",
        "status": BLOCKED if blockers else READY,
        "bundle_id": descriptor.get("bundle_id"),
        "bundle_version": descriptor.get("bundle_version"),
        "baseline_commit_sha": descriptor.get("baseline_commit_sha"),
        "descriptor_sha256": canonical_hash(descriptor),
        "contract_sha256": contract["contract_sha256"],
        "d50_status_sha256": d50_status.get("status_sha256"),
        "scopes": descriptor.get("scopes"),
        "source_roles_present": sorted(set(partition_roles)),
        "partition_summaries": sorted(partition_summaries, key=lambda item: str(item["partition_id"])),
        "file_inventory": sorted(file_inventory, key=lambda item: (str(item["path"]), str(item["kind"]))),
        "blocking_reasons": blockers,
        "historical_recovery": {
            "recovered_partition_count": recovered_count,
            "prospective_rows_credited": 0,
            "backfill_performed": False,
        },
        "explicit_review_required": True,
        "source_admitted": False,
        "official_dataset_sealed": False,
        "official_challenger_runs_allowed": False,
        "economics_allowed": False,
        "safety": dict(OUTPUT_SAFETY),
        "isolation": {
            "delta_mutations": 0,
            "regime_mutations": 0,
            "b3_mutations": 0,
            "incumbent_mutations": 0,
            "runtime_mutations": 0,
        },
        "next_action": (
            "REQUEST_EXPLICIT_SOURCE_ADMISSION_REVIEW_WITHOUT_SEAL"
            if not blockers
            else "CORRECT_SOURCE_BUNDLE_AND_RERUN_FAIL_CLOSED_PREFLIGHT"
        ),
    }
    payload["assessment_sha256"] = canonical_hash(payload)
    return payload


def build_current_preflight(inventory: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Map the current CP7 inventory to CP8 admission requirements, read-only."""
    contract_errors = validate_contract(contract)
    if contract_errors:
        raise RuntimeError("invalid frozen source admission contract: " + "; ".join(contract_errors))
    errors: list[str] = []
    if inventory.get("schema") != EVIDENCE_INVENTORY_SCHEMA:
        errors.append("EVIDENCE_INVENTORY_SCHEMA_INVALID")
    _verify_self_hash(inventory, "inventory_sha256", "EVIDENCE_INVENTORY_HASH_INVALID", errors)
    if inventory.get("admissible_candidate_count") != 0:
        errors.append("CP7_INVENTORY_EXPECTED_ZERO_CANDIDATES")
    safety = inventory.get("safety")
    if not isinstance(safety, dict):
        errors.append("EVIDENCE_INVENTORY_SAFETY_INVALID")
    else:
        for key, expected in CURRENT_INVENTORY_SAFETY.items():
            if safety.get(key) != expected:
                errors.append(f"EVIDENCE_INVENTORY_SAFETY_{key.upper()}")
    d50 = inventory.get("d50")
    if not isinstance(d50, dict):
        errors.append("EVIDENCE_INVENTORY_D50_INVALID")
        d50 = {}
    claims_raw = d50.get("source_hashes")
    if not isinstance(claims_raw, dict) or sorted(claims_raw) != ["funding", "ohlc"]:
        errors.append("EVIDENCE_INVENTORY_D50_HASHES_INVALID")
        claims_raw = {}
    claims = {str(key).upper(): str(value) for key, value in claims_raw.items()}
    physical = inventory.get("physical_evidence")
    if not isinstance(physical, list):
        errors.append("EVIDENCE_INVENTORY_PHYSICAL_LIST_INVALID")
        physical = []
    matches: dict[str, list[str]] = {}
    for role in SOURCE_ROLES:
        claimed = claims.get(role)
        matches[role] = sorted(
            str(item.get("path"))
            for item in physical
            if isinstance(item, dict) and item.get("sha256") == claimed
        )
    manual = inventory.get("manual_market_evidence")
    if not isinstance(manual, dict):
        errors.append("EVIDENCE_INVENTORY_MANUAL_MARKET_INVALID")
        manual = {}
    recoverable_ohlc = []
    for item in manual.get("files", []) if isinstance(manual.get("files"), list) else []:
        if not isinstance(item, dict) or item.get("asset") != "BTC" or not item.get("rows"):
            continue
        recoverable_ohlc.append(
            {
                "path": item.get("path"),
                "venue": item.get("venue"),
                "rows": item.get("rows"),
                "last_observation_utc": item.get("last_observation_utc"),
                "d50_hash_match": item.get("path") in matches["OHLC"],
                "available_at_bound": False,
                "formal_schema_bound": False,
                "source_provenance_bound": False,
            }
        )
    blockers = {
        "BTC_CORE_EXPECTED_CUTOFF_NOT_MET",
        "CAUSAL_AVAILABILITY_NOT_BOUND",
        "CURRENT_INVENTORY_HAS_NO_ADMISSIBLE_PARTITION",
        "PARTIAL_ROLE_ADMISSION_PROHIBITED",
        "SOURCE_ADMISSION_BUNDLE_NOT_SUPPLIED",
        "SOURCE_ADMISSION_PROVENANCE_NOT_BOUND",
        "SOURCE_ADMISSION_SCHEMA_NOT_BOUND",
    }
    for role in SOURCE_ROLES:
        if not matches[role]:
            blockers.add(f"D50_{role}_CLAIM_HAS_NO_EXACT_PHYSICAL_MATCH")
    blockers.update(errors)
    payload: dict[str, Any] = {
        "schema": CURRENT_PREFLIGHT_SCHEMA,
        "assessment_kind": "CURRENT_EVIDENCE_TO_SOURCE_ADMISSION_GAP_ONLY",
        "status": CURRENT_BLOCKED,
        "runtime_commit": inventory.get("runtime_commit"),
        "contract_sha256": contract["contract_sha256"],
        "evidence_inventory_sha256": inventory.get("inventory_sha256"),
        "expected_cutoff": inventory.get("expected_cutoff"),
        "d50_claimed_source_hashes": claims,
        "exact_physical_hash_matches": matches,
        "recoverable_manual_btc_ohlc": sorted(recoverable_ohlc, key=lambda item: str(item["path"])),
        "complete_role_count": sum(bool(matches[role]) for role in SOURCE_ROLES),
        "admissible_source_bundle_count": 0,
        "blocking_reasons": sorted(blockers),
        "explicit_review_required": True,
        "source_admitted": False,
        "official_dataset_sealed": False,
        "economics_allowed": False,
        "prospective_rows_credited": 0,
        "safety": dict(OUTPUT_SAFETY),
        "isolation": {
            "delta_mutations": 0,
            "regime_mutations": 0,
            "b3_mutations": 0,
            "incumbent_mutations": 0,
            "runtime_mutations": 0,
        },
        "next_action": "RECOVER_EXACT_D50_BYTES_OR_START_FORWARD_ONLY_CAPTURE_THEN_BIND_SCHEMA_PROVENANCE_AND_CAUSAL_AVAILABILITY",
    }
    payload["preflight_sha256"] = canonical_hash(payload)
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
        if os.environ.get(key, expected).lower() != expected:
            raise RuntimeError(f"unsafe environment field {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--current-inventory", type=Path)
    mode.add_argument("--bundle", type=Path)
    parser.add_argument("--bundle-root", type=Path)
    parser.add_argument("--d50-status", type=Path)
    args = parser.parse_args()
    _assert_safe_environment()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if args.current_inventory:
        if args.bundle_root or args.d50_status:
            parser.error("--bundle-root/--d50-status are only valid with --bundle")
        inventory = json.loads(args.current_inventory.read_text(encoding="utf-8"))
        payload = build_current_preflight(inventory, contract)
    else:
        if args.bundle_root is None or args.d50_status is None:
            parser.error("--bundle requires --bundle-root and --d50-status")
        descriptor = json.loads(args.bundle.read_text(encoding="utf-8"))
        d50_status = json.loads(args.d50_status.read_text(encoding="utf-8"))
        payload = build_source_admission(args.bundle_root, descriptor, d50_status, contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_admitted": False,
                "official_dataset_sealed": False,
                "economics_allowed": False,
                "prospective_rows_credited": 0,
                "orders_generated": 0,
                "real_capital_used": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
