"""Shared fail-closed helpers for GATE BTC prospective measurements."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from tools.gate_btc_prospective_ledgers import append_gateway

STRATEGIES = ("QOS_Moderada", "QOS_Ultra")
VARIANTS = ("NO_LOCK_CONTROL", "LOCK25", "LOCK50")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def payload_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: dict[str, Any], field: str) -> str:
    clean = dict(value)
    clean.pop(field, None)
    return payload_sha(clean)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def iso_day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(f"invalid {field}: {value}") from exc


def snapshot_paths(ledger_dir: Path) -> list[Path]:
    return sorted((ledger_dir / "snapshots").glob("*.json"))


def write_immutable(path: Path, value: dict[str, Any], hash_field: str) -> bool:
    if not path.exists():
        atomic_json(path, value)
        return False
    existing = load_json(path)
    require(existing.get(hash_field) == canonical_sha(existing, hash_field), f"invalid existing hash: {path}")
    require(existing == value, f"immutable file differs: {path}")
    return True


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("status") == "FROZEN_READY_FOR_PROSPECTIVE_LEDGER", "LOCK contract not frozen")
    require(contract.get("research_only") is True, "research_only changed")
    require(contract.get("shadow_only") is True, "shadow_only changed")
    require(contract.get("not_approved") is True, "not_approved changed")
    require(contract.get("orders") == 0 and contract.get("capital") == 0, "orders/capital must remain zero")
    require(contract.get("promotion") == "PROHIBITED", "promotion must remain prohibited")
    require(contract.get("control", {}).get("name") == "NO_LOCK_CONTROL", "control changed")
    expected = {"LOCK25": (1.25, 0.25, 0.10), "LOCK50": (1.50, 0.50, 0.15)}
    for name, (arm, share, retracement) in expected.items():
        cfg = contract.get("variants", {}).get(name, {})
        require(float(cfg.get("arming_level_multiple", -1)) == arm, f"{name} arming changed")
        require(float(cfg.get("protected_share_of_accumulated_profit", -1)) == share, f"{name} share changed")
        require(float(cfg.get("retracement_trigger_pct", -1)) == retracement, f"{name} retracement changed")
        require(cfg.get("destination") == "VIRTUAL_CASH", f"{name} destination changed")
        require(cfg.get("double_counting_prohibited") is True, f"{name} double-counting guard missing")
    cycle = contract.get("cycle", {})
    require(cycle.get("reset_rule") == "EXPLICIT_USER_DECISION_ONLY", "reset rule changed")
    require(cycle.get("automatic_monthly_reset") is False, "automatic reset prohibited")


def safe_gateway(args) -> int:
    """Do not count the same Gateway source close twice."""
    manifest = load_json(args.manifest)
    source_close = iso_day(str(manifest.get("data_as_of")), "Gateway data_as_of")
    paths = snapshot_paths(args.ledger_dir)
    if paths:
        previous = load_json(paths[-1])
        previous_close = iso_day(str(previous.get("data_as_of")), "previous Gateway data_as_of")
        require(source_close >= previous_close, "Gateway source close moved backwards")
        if source_close == previous_close:
            current_sources = {
                "manifest": file_sha(args.manifest),
                "snapshot_status": file_sha(args.snapshot_status),
                "compositions": file_sha(args.compositions),
                "execution_profiles": file_sha(args.execution_profiles),
            }
            previous_sources = previous.get("source_artifacts", {})
            identical = set(current_sources.values()).issubset(set(previous_sources.values()))
            bundle_sha = payload_sha(current_sources)
            diagnostic = {
                "schema": "gate_btc.gateway_same_source_close_diagnostic.v1",
                "status": "IDENTICAL_ALREADY_RECORDED" if identical else "NONIDENTICAL_SAME_SOURCE_CLOSE_NOT_COUNTED",
                "source_data_as_of": source_close.isoformat(),
                "existing_snapshot_id": previous.get("snapshot_id"),
                "existing_sequence": previous.get("sequence"),
                "existing_snapshot_sha256": previous.get("snapshot_sha256"),
                "existing_source_artifacts": previous_sources,
                "candidate_source_artifacts": current_sources,
                "candidate_bundle_sha256": bundle_sha,
                "counter_incremented": False,
                "snapshot_mutation_performed": False,
                "required_action": "none; wait for a strictly newer source close",
                "research_only": True, "shadow_only": True, "not_approved": True,
                "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
            }
            diagnostic["diagnostic_sha256"] = canonical_sha(diagnostic, "diagnostic_sha256")
            write_immutable(
                args.ledger_dir / "diagnostics" / f"{source_close.isoformat()}-{bundle_sha[:12]}.json",
                diagnostic, "diagnostic_sha256",
            )
            diagnostic_count = len(list((args.ledger_dir / "diagnostics").glob("*.json")))
            existing_status_path = args.ledger_dir / "STATUS.json"
            existing_status = load_json(existing_status_path) if existing_status_path.exists() else {}
            atomic_json(existing_status_path, {
                "schema": "gate_btc.gateway_dynamics_ledger_status.v2",
                "updated_at_utc": manifest.get("run_utc") or existing_status.get("updated_at_utc"),
                "status": "ACTIVE",
                "valid_snapshot_count": int(previous.get("sequence", 0)),
                "required_snapshot_count": int(existing_status.get("required_snapshot_count", 80)),
                "latest_snapshot_id": previous.get("snapshot_id"),
                "latest_source_data_as_of": previous_close.isoformat(),
                "latest_snapshot_sha256": previous.get("snapshot_sha256"),
                "next_expected_source_data_as_of": (previous_close + timedelta(days=1)).isoformat(),
                "same_source_close_diagnostic_count": diagnostic_count,
                "same_source_close_counter_incremented": False,
                "raw_snapshots_are_not_automatically_counted": True,
                "research_only": True, "shadow_only": True, "not_approved": True,
                "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
            })
            print(json.dumps({
                "result": "SKIPPED_ALREADY_RECORDED_SOURCE_CLOSE" if identical else "SKIPPED_NONIDENTICAL_SAME_SOURCE_CLOSE",
                **diagnostic,
            }, indent=2))
            return 0
    require(args.snapshot_id == source_close.isoformat(), "Gateway snapshot_id must equal source data_as_of")
    return append_gateway(args)


def deep_diff(left: Any, right: Any, path: str = "$") -> list[dict[str, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}"
            if key not in left:
                result.append({"path": child, "kind": "ADDED_IN_CANDIDATE", "frozen": None, "candidate": right[key]})
            elif key not in right:
                result.append({"path": child, "kind": "MISSING_IN_CANDIDATE", "frozen": left[key], "candidate": None})
            else:
                result.extend(deep_diff(left[key], right[key], child))
        return result
    if isinstance(left, list) and isinstance(right, list):
        result = []
        if len(left) != len(right):
            result.append({"path": path, "kind": "LIST_LENGTH_CHANGED", "frozen": len(left), "candidate": len(right)})
        for index, (a, b) in enumerate(zip(left, right)):
            result.extend(deep_diff(a, b, f"{path}[{index}]"))
        return result
    return [] if left == right else [{"path": path, "kind": "VALUE_CHANGED", "frozen": left, "candidate": right}]
