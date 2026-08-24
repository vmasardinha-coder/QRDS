#!/usr/bin/env python3
"""Deterministic official-dataset admission manifest for GATE BTC 2.0.

The builder inventories exact bytes, tabular schemas and source provenance.  It
can only produce a candidate that is ready for explicit seal review; it never
self-seals a dataset, feeds an engine, runs economics, mutates canonical data or
unlocks a challenger.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "gate_btc.2_0.official_dataset_contract.v1"
DESCRIPTOR_SCHEMA = "gate_btc.2_0.official_dataset_descriptor.v1"
TABULAR_SCHEMA = "gate_btc.2_0.tabular_dataset_schema.v1"
SOURCE_PROVENANCE_SCHEMA = "gate_btc.2_0.source_provenance.v1"
READINESS_SCHEMA = "gate_btc.2_0.dataset_seal_readiness.v1"
MANIFEST_SCHEMA = "gate_btc.2_0.official_dataset_manifest.v1"
READY = "READY_FOR_EXPLICIT_SEAL_REVIEW"
BLOCKED = "BLOCKED_NOT_READY_FOR_SEAL_REVIEW"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OBSERVED_KINDS = {"observed", "derived"}

OUTPUT_SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "economic_calibration_performed": False,
    "official_challenger_runs_executed": 0,
    "canonical_data_writes": 0,
    "incumbent_mutations": 0,
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


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return payload, raw


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("CONTRACT_SCHEMA_INVALID")
    if contract.get("status") != "FROZEN_DATA_READINESS_ONLY":
        errors.append("CONTRACT_STATUS_INVALID")
    if contract.get("contract_version") != 1:
        errors.append("CONTRACT_VERSION_INVALID")
    if contract.get("allowed_formats") != ["csv", "jsonl"]:
        errors.append("CONTRACT_FORMATS_INVALID")
    required_scopes = contract.get("required_readiness_scopes")
    if required_scopes != [
        "BTC_CORE",
        "D50_ECONOMIC",
        "D50_QUALIFIED",
        "MULTIASSET_V2A",
    ]:
        errors.append("CONTRACT_READINESS_SCOPES_INVALID")
    if contract.get("allowed_dataset_scopes") != ["BTC_CORE", "MULTIASSET_V2A"]:
        errors.append("CONTRACT_DATASET_SCOPES_INVALID")
    if contract.get("source_provenance_schema") != SOURCE_PROVENANCE_SCHEMA:
        errors.append("CONTRACT_SOURCE_PROVENANCE_SCHEMA_INVALID")
    if contract.get("safety") != CONTRACT_SAFETY:
        errors.append("CONTRACT_SAFETY_INVALID")
    policies = contract.get("policies", {})
    expected_policies = {
        "canonical_dataset_write_allowed": False,
        "economic_calibration_allowed": False,
        "future_known_metadata_allowed": False,
        "late_seal_allowed": False,
        "partial_scope_seal_allowed": False,
        "retrospective_backfill_allowed": False,
        "seal_requires_explicit_review": True,
    }
    if policies != expected_policies:
        errors.append("CONTRACT_POLICIES_INVALID")
    unsigned = dict(contract)
    claimed = unsigned.pop("contract_sha256", None)
    if not HEX64.fullmatch(str(claimed)) or claimed != canonical_hash(unsigned):
        errors.append("CONTRACT_HASH_INVALID")
    return sorted(set(errors))


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
    root_resolved = root.resolve()
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError):
        errors.append(code)
        return None
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
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


def _required_fields(
    payload: Any,
    fields: list[str],
    prefix: str,
    errors: list[str],
) -> bool:
    if not isinstance(payload, dict):
        errors.append(f"{prefix}_NOT_OBJECT")
        return False
    missing = [field for field in fields if field not in payload]
    if missing:
        errors.extend(f"{prefix}_MISSING_{field.upper()}" for field in missing)
        return False
    return True


def _read_rows(
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
        if any(set(row) != set(columns) or None in row for row in rows):
            errors.append(f"PARTITION_{partition_id}_COLUMN_SCHEMA_MISMATCH")
    elif fmt == "jsonl":
        rows = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"PARTITION_{partition_id}_JSONL_INVALID_{line_number}")
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


def _validate_tabular_schema(
    schema: dict[str, Any],
    fmt: str,
    contract: dict[str, Any],
    partition_id: str,
    errors: list[str],
) -> tuple[list[str], list[str], str | None, str | None]:
    spec = contract["tabular_schema_contract"]
    if not _required_fields(
        schema,
        spec["required_fields"],
        f"SCHEMA_{partition_id}",
        errors,
    ):
        return [], [], None, None
    if schema.get("schema") != TABULAR_SCHEMA:
        errors.append(f"SCHEMA_{partition_id}_IDENTIFIER_INVALID")
    if schema.get("format") != fmt:
        errors.append(f"SCHEMA_{partition_id}_FORMAT_MISMATCH")
    if schema.get("timezone") != "UTC":
        errors.append(f"SCHEMA_{partition_id}_TIMEZONE_NOT_UTC")
    if schema.get("economic_fields") != []:
        errors.append(f"SCHEMA_{partition_id}_ECONOMIC_FIELDS_FORBIDDEN")
    if schema.get("future_known_metadata_allowed") is not False:
        errors.append(f"SCHEMA_{partition_id}_FUTURE_METADATA_UNSAFE")

    columns_payload = schema.get("columns")
    if not isinstance(columns_payload, list) or not columns_payload:
        errors.append(f"SCHEMA_{partition_id}_COLUMNS_INVALID")
        return [], [], None, None
    columns: list[str] = []
    role_to_names: dict[str, list[str]] = {}
    for index, column in enumerate(columns_payload):
        prefix = f"SCHEMA_{partition_id}_COLUMN_{index}"
        if not _required_fields(column, spec["column_required_fields"], prefix, errors):
            continue
        name = column.get("name")
        role = column.get("role")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}_NAME_INVALID")
            continue
        if not isinstance(column.get("type"), str) or not column.get("type"):
            errors.append(f"{prefix}_TYPE_INVALID")
        if not isinstance(role, str) or not role:
            errors.append(f"{prefix}_ROLE_INVALID")
            continue
        columns.append(name)
        role_to_names.setdefault(role, []).append(name)
    if len(columns) != len(set(columns)):
        errors.append(f"SCHEMA_{partition_id}_DUPLICATE_COLUMNS")

    primary_key = schema.get("primary_key")
    if (
        not isinstance(primary_key, list)
        or not primary_key
        or any(not isinstance(field, str) or field not in columns for field in primary_key)
    ):
        errors.append(f"SCHEMA_{partition_id}_PRIMARY_KEY_INVALID")
        primary_key = []
    observation = role_to_names.get("observation_timestamp", [])
    available = role_to_names.get("available_at", [])
    if len(observation) != 1:
        errors.append(f"SCHEMA_{partition_id}_OBSERVATION_TIMESTAMP_ROLE_INVALID")
    if len(available) != 1:
        errors.append(f"SCHEMA_{partition_id}_AVAILABLE_AT_ROLE_INVALID")
    return (
        columns,
        primary_key,
        observation[0] if len(observation) == 1 else None,
        available[0] if len(available) == 1 else None,
    )


def build_manifest(
    dataset_root: Path,
    descriptor: dict[str, Any],
    readiness: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    contract_errors = validate_contract(contract)
    if contract_errors:
        raise RuntimeError("invalid frozen dataset contract: " + "; ".join(contract_errors))

    errors: list[str] = []
    readiness_blockers: list[str] = []
    required_scopes = contract["required_readiness_scopes"]

    if readiness.get("schema") != READINESS_SCHEMA:
        errors.append("READINESS_SCHEMA_INVALID")
    if readiness.get("assessment_kind") != "READINESS_ONLY_NOT_A_DATASET_SEAL":
        errors.append("READINESS_KIND_INVALID")
    readiness_unsigned = dict(readiness)
    readiness_claimed = readiness_unsigned.pop("assessment_sha256", None)
    if (
        not HEX64.fullmatch(str(readiness_claimed))
        or readiness_claimed != canonical_hash(readiness_unsigned)
    ):
        errors.append("READINESS_HASH_INVALID")
    for key, expected in {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "stage_3_dataset_sealed": False,
        "official_challenger_runs_allowed": False,
    }.items():
        if readiness.get(key) != expected:
            errors.append(f"READINESS_SAFETY_{key.upper()}")
    tracks = readiness.get("tracks")
    if not isinstance(tracks, dict):
        errors.append("READINESS_TRACKS_INVALID")
        tracks = {}
    for scope in required_scopes:
        track = tracks.get(scope)
        if not isinstance(track, dict):
            readiness_blockers.append(f"READINESS_SCOPE_MISSING:{scope}")
            continue
        if track.get("status") != "READY_FOR_SCOPED_DATASET_MANIFEST":
            readiness_blockers.append(f"READINESS_SCOPE_BLOCKED:{scope}")
            blockers = track.get("blockers")
            if isinstance(blockers, list):
                readiness_blockers.extend(
                    f"READINESS:{scope}:{code}"
                    for code in blockers
                    if isinstance(code, str)
                )
    if readiness.get("status") != "READY_FOR_SCOPED_DATASET_MANIFEST":
        readiness_blockers.append("READINESS_GLOBAL_STATUS_NOT_READY")
    if readiness.get("hard_failures") != []:
        readiness_blockers.append("READINESS_HARD_FAILURES_PRESENT")
    if readiness.get("delivery_gaps") != []:
        readiness_blockers.append("READINESS_DELIVERY_GAPS_PRESENT")
    if set(readiness.get("ready_scopes", [])) != set(required_scopes):
        readiness_blockers.append("READINESS_READY_SCOPE_SET_INCOMPLETE")
    if readiness.get("blocked_scopes") != []:
        readiness_blockers.append("READINESS_BLOCKED_SCOPES_PRESENT")

    descriptor_fields = contract["descriptor_required_fields"]
    _required_fields(descriptor, descriptor_fields, "DESCRIPTOR", errors)
    if descriptor.get("schema") != DESCRIPTOR_SCHEMA:
        errors.append("DESCRIPTOR_SCHEMA_INVALID")
    if descriptor.get("contract_sha256") != contract["contract_sha256"]:
        errors.append("DESCRIPTOR_CONTRACT_HASH_MISMATCH")
    if not HEX40.fullmatch(str(descriptor.get("baseline_commit_sha", ""))):
        errors.append("DESCRIPTOR_BASELINE_SHA_INVALID")
    created_at = _utc(descriptor.get("created_at_utc"), "DESCRIPTOR_CREATED_AT_INVALID", errors)
    cutoff = _utc(descriptor.get("cutoff_utc"), "DESCRIPTOR_CUTOFF_INVALID", errors)
    if created_at and cutoff and created_at < cutoff:
        errors.append("DESCRIPTOR_CREATED_BEFORE_CUTOFF")
    if cutoff and readiness.get("expected_cutoff") != cutoff.date().isoformat():
        errors.append("DESCRIPTOR_READINESS_CUTOFF_MISMATCH")
    if descriptor.get("required_readiness_scopes") != required_scopes:
        errors.append("DESCRIPTOR_READINESS_SCOPES_MISMATCH")
    if descriptor.get("policies") != contract["policies"]:
        errors.append("DESCRIPTOR_POLICIES_MISMATCH")
    if descriptor.get("safety") != contract["safety"]:
        errors.append("DESCRIPTOR_SAFETY_MISMATCH")
    for field in ("dataset_id", "dataset_version"):
        if not isinstance(descriptor.get(field), str) or not descriptor[field]:
            errors.append(f"DESCRIPTOR_{field.upper()}_INVALID")

    sources_payload = descriptor.get("sources")
    if not isinstance(sources_payload, list) or not sources_payload:
        errors.append("DESCRIPTOR_SOURCES_INVALID")
        sources_payload = []
    sources: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources_payload):
        prefix = f"SOURCE_{index}"
        if not _required_fields(source, contract["source_required_fields"], prefix, errors):
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}_ID_INVALID")
            continue
        if source_id in sources:
            errors.append(f"SOURCE_DUPLICATE_ID:{source_id}")
            continue
        if source.get("observed_or_derived") not in OBSERVED_KINDS:
            errors.append(f"SOURCE_{source_id}_KIND_INVALID")
        if source.get("timezone") != "UTC":
            errors.append(f"SOURCE_{source_id}_TIMEZONE_NOT_UTC")
        if source.get("immutable_reference") is not True:
            errors.append(f"SOURCE_{source_id}_REFERENCE_NOT_IMMUTABLE")
        for field in (
            "provider",
            "source_reference",
            "access_class",
            "license_status",
            "causal_availability_rule",
        ):
            if not isinstance(source.get(field), str) or not source[field]:
                errors.append(f"SOURCE_{source_id}_{field.upper()}_INVALID")
        expected_provenance_sha = source.get("expected_provenance_sha256")
        if not HEX64.fullmatch(str(expected_provenance_sha)):
            errors.append(f"SOURCE_{source_id}_EXPECTED_PROVENANCE_SHA256_INVALID")
        provenance_path = _safe_file(
            dataset_root,
            source.get("provenance_path"),
            f"SOURCE_{source_id}_PROVENANCE_PATH_INVALID",
            errors,
        )
        source_entry = dict(source)
        if provenance_path is not None:
            raw_provenance = provenance_path.read_bytes()
            provenance_sha = _sha256(raw_provenance)
            source_entry["provenance_sha256"] = provenance_sha
            source_entry["provenance_byte_length"] = len(raw_provenance)
            if provenance_sha != expected_provenance_sha:
                errors.append(f"SOURCE_{source_id}_PROVENANCE_HASH_MISMATCH")
            try:
                provenance_payload = json.loads(raw_provenance)
            except json.JSONDecodeError:
                errors.append(f"SOURCE_{source_id}_PROVENANCE_JSON_INVALID")
                provenance_payload = None
            if not isinstance(provenance_payload, dict):
                errors.append(f"SOURCE_{source_id}_PROVENANCE_NOT_OBJECT")
            else:
                if provenance_payload.get("schema") != SOURCE_PROVENANCE_SCHEMA:
                    errors.append(f"SOURCE_{source_id}_PROVENANCE_SCHEMA_INVALID")
                for field in (
                    "source_id",
                    "provider",
                    "source_reference",
                    "access_class",
                    "license_status",
                    "observed_or_derived",
                    "timezone",
                    "causal_availability_rule",
                    "immutable_reference",
                ):
                    if provenance_payload.get(field) != source.get(field):
                        errors.append(f"SOURCE_{source_id}_PROVENANCE_FIELD_MISMATCH:{field}")
        sources[source_id] = source_entry

    partitions_payload = descriptor.get("partitions")
    if not isinstance(partitions_payload, list) or not partitions_payload:
        errors.append("DESCRIPTOR_PARTITIONS_INVALID")
        partitions_payload = []
    partition_ids: set[str] = set()
    relative_paths: set[str] = set()
    schema_entries: dict[str, dict[str, Any]] = {}
    file_entries: list[dict[str, Any]] = []
    represented_scopes: set[str] = set()
    referenced_source_ids: set[str] = set()

    for index, partition in enumerate(partitions_payload):
        prefix = f"PARTITION_{index}"
        if not _required_fields(partition, contract["partition_required_fields"], prefix, errors):
            continue
        partition_id = partition.get("partition_id")
        if not isinstance(partition_id, str) or not partition_id:
            errors.append(f"{prefix}_ID_INVALID")
            continue
        if partition_id in partition_ids:
            errors.append(f"PARTITION_DUPLICATE_ID:{partition_id}")
            continue
        partition_ids.add(partition_id)
        scope = partition.get("scope")
        if scope not in contract["allowed_dataset_scopes"]:
            errors.append(f"PARTITION_{partition_id}_SCOPE_INVALID")
        else:
            represented_scopes.add(scope)
        fmt = partition.get("format")
        if fmt not in contract["allowed_formats"]:
            errors.append(f"PARTITION_{partition_id}_FORMAT_INVALID")
        source_id = partition.get("source_id")
        source = sources.get(source_id)
        if source is None:
            errors.append(f"PARTITION_{partition_id}_SOURCE_MISSING")
        elif partition.get("observed_or_derived") != source.get("observed_or_derived"):
            errors.append(f"PARTITION_{partition_id}_SOURCE_KIND_MISMATCH")
        if isinstance(source_id, str):
            referenced_source_ids.add(source_id)
        if not isinstance(partition.get("granularity"), str) or not partition["granularity"]:
            errors.append(f"PARTITION_{partition_id}_GRANULARITY_INVALID")
        for field in ("expected_sha256", "expected_schema_sha256"):
            if not HEX64.fullmatch(str(partition.get(field, ""))):
                errors.append(f"PARTITION_{partition_id}_{field.upper()}_INVALID")

        relative_path = partition.get("relative_path")
        if isinstance(relative_path, str) and relative_path in relative_paths:
            errors.append(f"PARTITION_DUPLICATE_PATH:{relative_path}")
        elif isinstance(relative_path, str):
            relative_paths.add(relative_path)
        data_path = _safe_file(
            dataset_root,
            relative_path,
            f"PARTITION_{partition_id}_DATA_PATH_INVALID",
            errors,
        )
        schema_path = _safe_file(
            dataset_root,
            partition.get("schema_path"),
            f"PARTITION_{partition_id}_SCHEMA_PATH_INVALID",
            errors,
        )
        if data_path is None or schema_path is None:
            continue

        raw_data = data_path.read_bytes()
        raw_schema = schema_path.read_bytes()
        data_sha = _sha256(raw_data)
        schema_sha = _sha256(raw_schema)
        if data_sha != partition.get("expected_sha256"):
            errors.append(f"PARTITION_{partition_id}_DATA_HASH_MISMATCH")
        if schema_sha != partition.get("expected_schema_sha256"):
            errors.append(f"PARTITION_{partition_id}_SCHEMA_HASH_MISMATCH")
        try:
            schema_payload = json.loads(raw_schema)
        except json.JSONDecodeError:
            errors.append(f"SCHEMA_{partition_id}_JSON_INVALID")
            continue
        if not isinstance(schema_payload, dict):
            errors.append(f"SCHEMA_{partition_id}_NOT_OBJECT")
            continue
        columns, primary_key, observation_field, available_field = _validate_tabular_schema(
            schema_payload,
            str(fmt),
            contract,
            partition_id,
            errors,
        )
        rows = _read_rows(raw_data, str(fmt), columns, partition_id, errors)
        seen_keys: set[tuple[str, ...]] = set()
        observation_values: list[datetime] = []
        available_values: list[datetime] = []
        for row_number, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            key = tuple(str(row.get(field, "")) for field in primary_key)
            if primary_key and (any(not value for value in key) or key in seen_keys):
                errors.append(f"PARTITION_{partition_id}_PRIMARY_KEY_INVALID_ROW_{row_number}")
            seen_keys.add(key)
            if observation_field:
                parsed = _utc(
                    row.get(observation_field),
                    f"PARTITION_{partition_id}_OBSERVATION_UTC_INVALID_ROW_{row_number}",
                    errors,
                )
                if parsed:
                    observation_values.append(parsed)
            if available_field:
                parsed = _utc(
                    row.get(available_field),
                    f"PARTITION_{partition_id}_AVAILABLE_AT_UTC_INVALID_ROW_{row_number}",
                    errors,
                )
                if parsed:
                    available_values.append(parsed)
            if observation_field and available_field:
                observation = _utc(row.get(observation_field), "", [])
                available = _utc(row.get(available_field), "", [])
                if observation and available and available < observation:
                    errors.append(f"PARTITION_{partition_id}_AVAILABLE_BEFORE_OBSERVATION_ROW_{row_number}")
                if cutoff and available and available > cutoff:
                    errors.append(f"PARTITION_{partition_id}_AVAILABLE_AFTER_CUTOFF_ROW_{row_number}")

        schema_id = schema_payload.get("schema_id")
        if not isinstance(schema_id, str) or not schema_id:
            errors.append(f"SCHEMA_{partition_id}_SCHEMA_ID_INVALID")
            schema_id = f"INVALID:{partition_id}"
        existing_schema = schema_entries.get(schema_id)
        schema_entry = {
            "schema_id": schema_id,
            "relative_path": partition["schema_path"],
            "sha256": schema_sha,
            "byte_length": len(raw_schema),
        }
        if existing_schema and existing_schema != schema_entry:
            errors.append(f"SCHEMA_ID_COLLISION:{schema_id}")
        else:
            schema_entries[schema_id] = schema_entry
        file_entries.append(
            {
                "partition_id": partition_id,
                "scope": scope,
                "relative_path": relative_path,
                "format": fmt,
                "source_id": source_id,
                "observed_or_derived": partition.get("observed_or_derived"),
                "granularity": partition.get("granularity"),
                "schema_id": schema_id,
                "schema_sha256": schema_sha,
                "sha256": data_sha,
                "byte_length": len(raw_data),
                "row_count": len(rows),
                "first_observation_utc": min(observation_values).isoformat().replace("+00:00", "Z")
                if observation_values
                else None,
                "last_observation_utc": max(observation_values).isoformat().replace("+00:00", "Z")
                if observation_values
                else None,
                "first_available_at_utc": min(available_values).isoformat().replace("+00:00", "Z")
                if available_values
                else None,
                "last_available_at_utc": max(available_values).isoformat().replace("+00:00", "Z")
                if available_values
                else None,
            }
        )

    if represented_scopes != set(contract["allowed_dataset_scopes"]):
        errors.append("DATASET_SCOPE_COVERAGE_INCOMPLETE")
    if referenced_source_ids != set(sources):
        errors.append("SOURCE_INVENTORY_NOT_EXACTLY_REFERENCED")

    source_inventory = [sources[key] for key in sorted(sources)]
    schema_inventory = [schema_entries[key] for key in sorted(schema_entries)]
    file_inventory = sorted(file_entries, key=lambda item: item["partition_id"])
    descriptor_sha = canonical_hash(descriptor)
    source_sha = canonical_hash(source_inventory)
    schema_bundle_sha = canonical_hash(schema_inventory)
    file_inventory_sha = canonical_hash(file_inventory)
    binding = {
        "contract_sha256": contract["contract_sha256"],
        "descriptor_sha256": descriptor_sha,
        "readiness_assessment_sha256": readiness_claimed,
        "source_provenance_sha256": source_sha,
        "schema_bundle_sha256": schema_bundle_sha,
        "file_inventory_sha256": file_inventory_sha,
    }
    dataset_sha = canonical_hash(binding)
    blockers = sorted(set(errors + readiness_blockers))
    status = READY if not blockers else BLOCKED
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "status": status,
        "admission_kind": "OFFICIAL_DATASET_CANDIDATE_NOT_A_SEAL",
        "dataset_id": descriptor.get("dataset_id"),
        "dataset_version": descriptor.get("dataset_version"),
        "baseline_commit_sha": descriptor.get("baseline_commit_sha"),
        "created_at_utc": descriptor.get("created_at_utc"),
        "cutoff_utc": descriptor.get("cutoff_utc"),
        "contract_sha256": contract["contract_sha256"],
        "descriptor_sha256": descriptor_sha,
        "readiness_assessment_sha256": readiness_claimed,
        "required_readiness_scopes": list(required_scopes),
        "represented_dataset_scopes": sorted(represented_scopes),
        "blocking_reasons": blockers,
        "source_inventory": source_inventory,
        "source_provenance_sha256": source_sha,
        "schema_inventory": schema_inventory,
        "schema_bundle_sha256": schema_bundle_sha,
        "file_inventory": file_inventory,
        "file_inventory_sha256": file_inventory_sha,
        "dataset_binding": binding,
        "dataset_sha256": dataset_sha,
        "official_dataset_sealed": False,
        "stage_3_dataset_sealed": False,
        "explicit_seal_review_required": True,
        "official_challenger_runs_allowed": False,
        "economics_consumed": False,
        "policies": dict(contract["policies"]),
        "safety": dict(OUTPUT_SAFETY),
        "next_action": (
            "EXPLICIT_REVIEW_OF_EXACT_DATASET_CANDIDATE"
            if status == READY
            else "REPAIR_REAL_READINESS_OR_PACKAGE_EVIDENCE_WITHOUT_BACKFILL"
        ),
    }
    manifest["manifest_sha256"] = canonical_hash(manifest)
    return manifest


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
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-review-ready", action="store_true")
    args = parser.parse_args()
    _assert_safe_environment()
    contract, _ = _load_json(args.contract)
    descriptor, _ = _load_json(args.descriptor)
    readiness, _ = _load_json(args.readiness)
    manifest = build_manifest(args.dataset_root, descriptor, readiness, contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "blocking_reason_count": len(manifest["blocking_reasons"]),
                "dataset_sha256": manifest["dataset_sha256"],
                "official_dataset_sealed": False,
                "official_challenger_runs_allowed": False,
                "economic_calibration_performed": False,
                "orders_generated": 0,
                "real_capital_used": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if args.require_review_ready and manifest["status"] != READY else 0


if __name__ == "__main__":
    raise SystemExit(main())
