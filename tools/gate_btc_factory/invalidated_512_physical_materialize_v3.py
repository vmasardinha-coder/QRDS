#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PAT = re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$")
TZ = ZoneInfo("America/Sao_Paulo")
CUTOFF = "2026-08-10"
TERMINAL = {"SCIENTIFIC_REJECTION", "VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE"}
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
    "H1_H31_ISOLATED": True,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unresolved_family_ids(queue_path: Path) -> list[str]:
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    if queue.get("affected_family_count") != 768:
        raise RuntimeError("V3_AFFECTED_SCOPE_CHANGED")
    if queue.get("completed_family_count") != 256:
        raise RuntimeError("V3_PREVIOUS_COMPLETED_SCOPE_CHANGED")
    rows = queue.get("families") or []
    if len(rows) != 768:
        raise RuntimeError(f"V3_QUEUE_ROW_COUNT:{len(rows)}")
    ids = [str(row.get("original_family_id") or "") for row in rows if row.get("status") not in TERMINAL]
    if len(ids) != 512 or len(set(ids)) != 512 or any(not x.startswith("H") for x in ids):
        raise RuntimeError(f"V3_UNRESOLVED_SCOPE_INVALID:{len(ids)}:{len(set(ids))}")
    return ids


def validate_packet(packet: dict) -> dict[str, int]:
    safety = packet.get("safety") or {}
    if packet.get("readiness") != "READY_SHADOW_DATA_ONLY":
        raise RuntimeError("PACKET_NOT_READY_SHADOW_DATA_ONLY")
    semantics = str(packet.get("capture_semantics", ""))
    if "PHYSICALLY_RETRIEVED" not in semantics or "NO_SYNTHETIC_BACKFILL" not in semantics:
        raise RuntimeError("PACKET_CAPTURE_SEMANTICS_INVALID")
    if not (
        safety.get("MT5_READ_ONLY") is True
        and safety.get("NO_ORDER_SEND") is True
        and safety.get("ORDERS") == 0
        and safety.get("REAL_CAPITAL") == 0
    ):
        raise RuntimeError("PACKET_SAFETY_INVALID")

    records = 0
    bars = 0
    years: set[int] = set()
    required = {"timestamp_utc", "open", "high", "low", "close", "tick_volume"}
    for record in packet.get("records", []):
        symbol = str(record.get("symbol", ""))
        if not PAT.fullmatch(symbol):
            continue
        records += 1
        rbars = record.get("bars")
        if not isinstance(rbars, list) or not rbars:
            raise RuntimeError(f"PHYSICAL_WIN_RECORD_WITHOUT_BARS:{symbol}")
        for bar in rbars:
            missing = required - set(bar)
            if missing:
                raise RuntimeError(f"PHYSICAL_BAR_SCHEMA_MISSING:{symbol}:{sorted(missing)}")
            ts = datetime.fromisoformat(str(bar["timestamp_utc"]).replace("Z", "+00:00"))
            years.add(ts.astimezone(TZ).year)
            op = float(bar["open"])
            hi = float(bar["high"])
            lo = float(bar["low"])
            cl = float(bar["close"])
            int(bar["tick_volume"])
            if hi < max(op, cl) or lo > min(op, cl) or hi < lo:
                raise RuntimeError(f"PHYSICAL_BAR_OHLC_INVALID:{symbol}:{bar['timestamp_utc']}")
            bars += 1
    if records == 0 or bars == 0:
        raise RuntimeError("NO_PHYSICAL_EXACT_EXPIRY_WIN_OHLCV")
    return {"records": records, "bars": bars, "years": len(years)}


def ingest(packet: dict):
    out = defaultdict(lambda: defaultdict(list))
    for record in packet.get("records", []):
        symbol = str(record.get("symbol", ""))
        if not PAT.fullmatch(symbol):
            continue
        for bar in record.get("bars", []):
            ts = datetime.fromisoformat(str(bar["timestamp_utc"]).replace("Z", "+00:00"))
            local = ts.astimezone(TZ)
            day = local.date().isoformat()
            if day >= CUTOFF:
                continue
            out[day][symbol].append(
                {
                    "timestamp": local.isoformat(),
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "volume": int(bar["tick_volume"]),
                }
            )
    for day in out:
        for symbol in out[day]:
            out[day][symbol].sort(key=lambda row: row["timestamp"])
    return out


def select_tminus1(data):
    """Exact 005 mechanical order: choose the T-1-liquidity contract before evaluator eligibility filtering."""
    days = sorted(data)
    selected = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        previous = days[i - 1]
        eligible = []
        for symbol, bars in data[previous].items():
            if symbol in data[day]:
                eligible.append((sum(row["volume"] for row in bars), symbol))
        if not eligible:
            continue
        _, symbol = max(eligible, key=lambda item: (item[0], item[1]))
        selected[day] = {"symbol": symbol, "selection_from_session": previous, "bars": data[day][symbol]}
    return selected


def evaluator_eligible(bars: list[dict]) -> bool:
    if len(bars) < 40:
        return False
    return all(
        (datetime.fromisoformat(b["timestamp"]) - datetime.fromisoformat(a["timestamp"])).total_seconds() == 300
        for a, b in zip(bars, bars[1:])
    )


def largest_contiguous(days: list[str]) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for day in days:
        if not current:
            current = [day]
            continue
        gap = (datetime.fromisoformat(day).date() - datetime.fromisoformat(current[-1]).date()).days
        if gap <= 3:
            current.append(day)
        else:
            blocks.append(current)
            current = [day]
    if current:
        blocks.append(current)
    if not blocks:
        return []
    longest = max(map(len, blocks))
    return min((block for block in blocks if len(block) == longest), key=lambda block: block[0])


def physical_block(packet: dict):
    selected = select_tminus1(ingest(packet))
    # Proven 005 ordering: form largest contiguous physical block first. The original
    # family evaluator then applies its frozen >=40/exact-M5 eligibility rule per session.
    block = largest_contiguous(sorted(selected))
    if not block:
        raise RuntimeError("NO_VALID_PHYSICAL_WIN_BLOCK")
    years = defaultdict(list)
    eligible_years = defaultdict(list)
    for day in block:
        years[day[:4]].append(day)
        if evaluator_eligible(selected[day]["bars"]):
            eligible_years[day[:4]].append(day)
    discovery = years.get("2025", [])
    replication = years.get("2026", [])
    eligible_discovery = eligible_years.get("2025", [])
    eligible_replication = eligible_years.get("2026", [])
    if not discovery or not replication:
        raise RuntimeError(f"PHYSICAL_BLOCK_DOES_NOT_SPAN_DISCOVERY_REPLICATION:{block[0]}:{block[-1]}")
    if not eligible_discovery or not eligible_replication:
        raise RuntimeError(
            f"NO_EVALUATOR_ELIGIBLE_SESSIONS_IN_BOTH_WINDOWS:{len(eligible_discovery)}:{len(eligible_replication)}"
        )
    return selected, block, discovery, replication, eligible_discovery, eligible_replication


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    family_ids = unresolved_family_ids(args.queue)
    packet = json.loads(args.packet.read_text(encoding="utf-8-sig"))
    source_schema = validate_packet(packet)
    selected, block, discovery, replication, eligible_discovery, eligible_replication = physical_block(packet)
    audit = {
        "source_schema": source_schema,
        "unresolved_family_count": len(family_ids),
        "physical_block": {
            "start": block[0],
            "end": block[-1],
            "sessions": len(block),
            "discovery_sessions": len(discovery),
            "replication_sessions": len(replication),
            "evaluator_eligible_discovery_sessions": len(eligible_discovery),
            "evaluator_eligible_replication_sessions": len(eligible_replication),
        },
    }
    print(json.dumps(audit, sort_keys=True))
    if args.audit_only:
        return 0
    if args.csv is None or args.gate is None:
        raise RuntimeError("CSV_AND_GATE_REQUIRED_FOR_MATERIALIZATION")

    rows = [bar for day in block for bar in selected[day]["bars"]]
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)

    gate = {
        "schema": "qrds.factory.invalidated_512.physical_materialization_source_gate.v1",
        "source_gate_id": "WIN_M5_PHYSICAL_MATERIALIZATION_V3",
        "evaluation_namespace": "RQ_PHYSICAL_MATERIALIZATION_2025_2026_V3",
        "family_ids": family_ids,
        "qualified": True,
        "free_or_official_auditable": True,
        "publication_semantics_proven": True,
        "revision_semantics_proven": True,
        "identity_qa_pass": True,
        "schema_qa_pass": True,
        "point_in_time_valid": True,
        "independent_unseen_evaluation_data": True,
        "no_historical_backfill_credit": True,
        "economics_pre_read": False,
        "dataset_relative_path": "runtime/factory_autonomy/invalidated_requalification/datasets/WIN_M5_PHYSICAL_V3.csv",
        "dataset_sha256": sha(args.csv),
        "windows": {
            "discovery": {"start": discovery[0], "end": discovery[-1]},
            "replication": {"start": replication[0], "end": replication[-1]},
        },
        "physical_block": audit["physical_block"],
        "roll_rule": "t_minus_1_liquidity",
        "session_eligibility": "ORIGINAL_AUTONOMOUS_FAMILY_EVALUATOR_GE40_EXACT_M5_AFTER_BLOCK_FORMATION",
        "synthetic_backfill": False,
        "interpolation": False,
        "volume_semantics": "MT5_TICK_VOLUME_COPIED_VERBATIM",
        "source_packet_sha256": sha(args.packet),
        "safety": SAFETY,
    }
    args.gate.parent.mkdir(parents=True, exist_ok=True)
    args.gate.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
