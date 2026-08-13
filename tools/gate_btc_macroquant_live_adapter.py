#!/usr/bin/env python3
"""Privacy-safe MacroQuant adapter for the GATE BTC Bull Replay live shadow.

Raw MacroQuant snapshots may contain real-capital NAV and live positions. This
adapter validates them locally/private-side and emits only a normalized index,
returns, timestamps, hashes and methodology identifiers. It never stores
absolute NAV or positions in public runtime evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64


class MacroQuantAdapterError(RuntimeError):
    pass


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise MacroQuantAdapterError(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise MacroQuantAdapterError(f"timestamp must be timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def load_contract(path: Path) -> dict:
    root = json.loads(path.read_text(encoding="utf-8"))
    cfg = root.get("live_shadow_v1", {}).get("macroquant_external")
    if not isinstance(cfg, dict) or cfg.get("schema") != "gate_btc.macroquant_external_adapter.v1":
        raise MacroQuantAdapterError("missing/wrong macroquant_external contract")
    if cfg.get("privacy", {}).get("public_runtime_must_not_store_absolute_nav") is not True:
        raise MacroQuantAdapterError("unsafe privacy contract: absolute NAV could be stored")
    if cfg.get("privacy", {}).get("public_runtime_must_not_store_positions") is not True:
        raise MacroQuantAdapterError("unsafe privacy contract: positions could be stored")
    return cfg


def load_snapshot(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise MacroQuantAdapterError(f"invalid snapshot JSON: {path}") from exc
    return payload, sha256_bytes(raw)


def validate_snapshot(payload: dict, cfg: dict, source_sha256: str, *, anchor: bool) -> dict:
    acc = cfg["acceptance"]
    checks = {
        "schema": payload.get("schema") == acc["required_snapshot_schema"],
        "strategy_name": payload.get("strategy_name") == acc["strategy_name"],
        "nav_currency": payload.get("nav_currency") == acc["nav_currency"],
        "research_only": payload.get("research_only") is True,
        "orders_zero": payload.get("orders_generated_for_gate_btc") == 0,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise MacroQuantAdapterError("snapshot contract failed: " + ",".join(failed))

    try:
        nav = float(payload["nav_net"])
    except Exception as exc:
        raise MacroQuantAdapterError("nav_net must be numeric") from exc
    if not (nav > 0):
        raise MacroQuantAdapterError("nav_net must be > 0")

    data_as_of = parse_utc(payload["data_as_of_utc"])
    generated_at = parse_utc(payload["generated_at_utc"])
    min_anchor = parse_utc(acc["minimum_anchor_data_as_of_utc"])
    if anchor and data_as_of < min_anchor:
        raise MacroQuantAdapterError(
            f"snapshot is pre-decision/stale for anchor: data_as_of={data_as_of.isoformat()} minimum={min_anchor.isoformat()}"
        )

    provenance = payload.get("source_provenance") or {}
    nav_type = str(provenance.get("nav_type") or "")
    if acc.get("require_native_nav") and "nativ" not in nav_type.lower():
        raise MacroQuantAdapterError("native NAV not established in source_provenance.nav_type")
    if acc.get("prohibit_reconstructed_history") and "reconstru" in nav_type.lower():
        raise MacroQuantAdapterError("reconstructed NAV prohibited")

    version = str(payload.get("strategy_version") or "").strip()
    if not version:
        raise MacroQuantAdapterError("strategy_version required")

    warnings = []
    capture = str(provenance.get("capture_method") or "")
    if "console" in capture.lower() or "colado" in capture.lower():
        warnings.append("MANUAL_CONSOLE_CAPTURE")
    if payload.get("fees_or_costs_today") is None:
        warnings.append("COST_INCLUSION_UNCONFIRMED")
    if payload.get("funding_today") is None:
        warnings.append("FUNDING_INCLUSION_UNCONFIRMED")
    if payload.get("daily_return_net") is None:
        warnings.append("DAILY_RETURN_NOT_NATIVE_IN_SNAPSHOT")

    return {
        "source_sha256": source_sha256,
        "data_as_of_utc": data_as_of.isoformat().replace("+00:00", "Z"),
        "generated_at_utc": generated_at.isoformat().replace("+00:00", "Z"),
        "strategy_version": version,
        "strategy_version_sha256": sha256_bytes(version.encode("utf-8")),
        "nav_net_private": nav,
        "capture_method": capture or None,
        "price_source": provenance.get("price_source"),
        "warnings": warnings,
    }


def row_hash(row: dict[str, Any]) -> str:
    return sha256_bytes(canonical({k: v for k, v in row.items() if k != "row_hash"}))


def read_ledger(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "observation_index", "data_as_of_utc", "elapsed_hours", "period_return_net",
        "normalized_nav", "source_sha256", "prior_source_sha256", "strategy_version_sha256",
        "prev_hash", "row_hash",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def anchor(snapshot_path: Path, contract_path: Path, output_dir: Path, received_at_utc: str) -> dict:
    cfg = load_contract(contract_path)
    payload, source_sha = load_snapshot(snapshot_path)
    meta = validate_snapshot(payload, cfg, source_sha, anchor=True)
    received = parse_utc(received_at_utc)
    output_dir.mkdir(parents=True, exist_ok=True)
    anchor_path = output_dir / "MACROQUANT_ANCHOR_REDACTED.json"
    if anchor_path.exists():
        existing = json.loads(anchor_path.read_text(encoding="utf-8"))
        if existing.get("source_sha256") == source_sha:
            return {"status": "ANCHOR_ALREADY_IDENTICAL", "anchor": existing}
        raise MacroQuantAdapterError("anchor already exists with different source")
    result = {
        "schema": "gate_btc.macroquant_anchor_redacted.v1",
        "status": "ANCHORED_WAITING_SECOND_SNAPSHOT",
        "join_data_as_of_utc": meta["data_as_of_utc"],
        "received_at_utc": received.isoformat().replace("+00:00", "Z"),
        "normalized_nav": 1.0,
        "source_sha256": source_sha,
        "strategy_version_sha256": meta["strategy_version_sha256"],
        "warnings": meta["warnings"],
        "privacy": "ABSOLUTE_NAV_AND_POSITIONS_NOT_STORED",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used_by_gate_btc": 0,
    }
    anchor_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": result["status"], "anchor": result}


def append(previous_path: Path, current_path: Path, contract_path: Path, output_dir: Path) -> dict:
    cfg = load_contract(contract_path)
    previous, previous_sha = load_snapshot(previous_path)
    current, current_sha = load_snapshot(current_path)
    p = validate_snapshot(previous, cfg, previous_sha, anchor=False)
    c = validate_snapshot(current, cfg, current_sha, anchor=False)
    if c["strategy_version"] != p["strategy_version"]:
        raise MacroQuantAdapterError("strategy version changed; start a separately labelled series")
    if current.get("methodology_changed_since_prior_snapshot") is True:
        raise MacroQuantAdapterError("methodology changed; cannot append to same series")
    pt = parse_utc(p["data_as_of_utc"])
    ct = parse_utc(c["data_as_of_utc"])
    if ct <= pt:
        raise MacroQuantAdapterError("current snapshot must be later than previous snapshot")

    anchor_path = output_dir / "MACROQUANT_ANCHOR_REDACTED.json"
    if not anchor_path.exists():
        raise MacroQuantAdapterError("missing redacted anchor")
    anchor_obj = json.loads(anchor_path.read_text(encoding="utf-8"))
    ledger_path = output_dir / "MACROQUANT_NORMALIZED_LEDGER.csv"
    ledger = read_ledger(ledger_path)
    if ledger:
        if ledger[-1]["source_sha256"] != previous_sha:
            raise MacroQuantAdapterError("previous snapshot does not match ledger tip")
        prev_norm = float(ledger[-1]["normalized_nav"])
        prev_hash = ledger[-1]["row_hash"]
        obs = int(ledger[-1]["observation_index"]) + 1
    else:
        if anchor_obj["source_sha256"] != previous_sha:
            raise MacroQuantAdapterError("previous snapshot does not match anchor")
        prev_norm = 1.0
        prev_hash = ZERO_HASH
        obs = 1

    period_return = c["nav_net_private"] / p["nav_net_private"] - 1.0
    native_return = current.get("daily_return_net")
    if native_return is not None:
        try:
            native_return = float(native_return)
        except Exception as exc:
            raise MacroQuantAdapterError("daily_return_net must be numeric when present") from exc
        if abs(native_return - period_return) > 1e-8:
            raise MacroQuantAdapterError(
                f"native daily_return_net mismatch: native={native_return} nav_ratio={period_return}"
            )

    elapsed_hours = (ct - pt).total_seconds() / 3600.0
    row = {
        "observation_index": obs,
        "data_as_of_utc": c["data_as_of_utc"],
        "elapsed_hours": f"{elapsed_hours:.8f}",
        "period_return_net": f"{period_return:.12g}",
        "normalized_nav": f"{prev_norm * (1 + period_return):.12g}",
        "source_sha256": current_sha,
        "prior_source_sha256": previous_sha,
        "strategy_version_sha256": c["strategy_version_sha256"],
        "prev_hash": prev_hash,
    }
    row["row_hash"] = row_hash(row)
    write_ledger(ledger_path, [*ledger, row])

    status = {
        "schema": "gate_btc.macroquant_live_shadow_status.v1",
        "status": "MACROQUANT_LIVE_DIAGNOSTIC_ACTIVE",
        "join_data_as_of_utc": anchor_obj["join_data_as_of_utc"],
        "latest_data_as_of_utc": c["data_as_of_utc"],
        "observations": obs,
        "normalized_nav": float(row["normalized_nav"]),
        "return_since_join": float(row["normalized_nav"]) - 1.0,
        "latest_period_return_net": period_return,
        "latest_elapsed_hours": elapsed_hours,
        "latest_source_sha256": current_sha,
        "ledger_tip_hash": row["row_hash"],
        "warnings": sorted(set(c["warnings"])),
        "privacy": "ABSOLUTE_NAV_AND_POSITIONS_NOT_STORED",
        "leaderboard_descriptive_only": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used_by_gate_btc": 0,
    }
    (output_dir / "MACROQUANT_STATUS_REDACTED.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_anchor = sub.add_parser("anchor")
    p_anchor.add_argument("--snapshot", required=True, type=Path)
    p_anchor.add_argument("--contract", required=True, type=Path)
    p_anchor.add_argument("--output-dir", required=True, type=Path)
    p_anchor.add_argument("--received-at-utc", required=True)
    p_append = sub.add_parser("append")
    p_append.add_argument("--previous-snapshot", required=True, type=Path)
    p_append.add_argument("--snapshot", required=True, type=Path)
    p_append.add_argument("--contract", required=True, type=Path)
    p_append.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = (
        anchor(args.snapshot, args.contract, args.output_dir, args.received_at_utc)
        if args.command == "anchor"
        else append(args.previous_snapshot, args.snapshot, args.contract, args.output_dir)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
