"""Pinned, additive H1 structural schedule; no market access or counter writes."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

EXTENSION_FILE = Path(__file__).resolve().parent / "gate_btc_factory/H1_PROSPECTIVE_SCHEDULE_EXTENSION_20261022.v1.json"
EXTENSION_SHA256 = "6e74e6357c3609491179b765c15b02d4fdadf26e2d4ff9add45546b31f325ce3"
PARENT_SHA256 = "9a78b234c6f00d64af9e9de1ad2d9aa3b6a28018965f35dcbbd1b0f58f3cdb3a"
PREFIX_SHA256 = "c9ff28b4d1b6c8e2aceb3281da51bc41858780493c99a0eeac148f2bdd0bc4f6"
FULL_SHA256 = "5fd7314f55fb1c6394628d94227fdc0ed375016a57453a07f05828ffd5a9282f"


def load_extension() -> dict:
    raw = EXTENSION_FILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXTENSION_SHA256:
        raise RuntimeError("H1_EXTENSION_HASH_MISMATCH")
    d = json.loads(raw)
    if d.get("schema") != "qrds.h1.prospective_schedule_extension.v1":
        raise RuntimeError("H1_EXTENSION_SCHEMA_MISMATCH")
    if (d.get("parent_amendment_sha256") != PARENT_SHA256
            or d.get("legacy_schedule_prefix_sha256") != PREFIX_SHA256
            or d.get("legacy_full_frozen_schedule_sha256") != FULL_SHA256):
        raise RuntimeError("H1_EXTENSION_LEGACY_SEALS_CHANGED")
    if (d.get("canonical_counter_preserved") != 17
            or d.get("canonical_last_qualified_session") != "2026-10-20"
            or d.get("continuity_policy") != "ADD_ONLY_UNIQUE_FUTURE_STRUCTURAL_PASS_STOP_AT_20"):
        raise RuntimeError("H1_EXTENSION_CONTINUITY_MISMATCH")
    expected_safety = {"research_only": True, "shadow_only": True, "economics_locked": True,
                       "no_backfill": True, "no_retune": True, "orders": 0,
                       "real_capital": 0, "engine_feed": False}
    if d.get("safety") != expected_safety:
        raise RuntimeError("H1_EXTENSION_SAFETY_MISMATCH")
    if d.get("qa_unchanged") != {"expected_m5_per_root": 102, "m1_to_m5_exact": True,
                                 "tick_grid": True, "ohlc_integrity": True}:
        raise RuntimeError("H1_EXTENSION_QA_CHANGED")
    rows = d.get("sessions", [])
    days = [r["date"] for r in rows]
    if (len(rows) != 5 or days != sorted(set(days))
            or days[0] != d.get("first_eligible_session")
            or any(day <= "2026-10-22" or date.fromisoformat(day).weekday() >= 5 for day in days)
            or any({"WIN": r["WIN"], "WDO": r["WDO"]} != {"WIN": "WINZ26", "WDO": "WDOX26"} for r in rows)):
        raise RuntimeError("H1_EXTENSION_SESSION_LIST_INVALID")
    registered = datetime.fromisoformat(d["preregistered_at_utc"].replace("Z", "+00:00"))
    start = datetime.combine(date.fromisoformat(days[0]), time(9), ZoneInfo("America/Sao_Paulo"))
    if registered.tzinfo is None or registered >= start:
        raise RuntimeError("H1_EXTENSION_NOT_FROZEN_BEFORE_FIRST_SESSION")
    if d.get("freeze_status") != "FROZEN_BEFORE_SESSION_EXTENSION_20261022_V1":
        raise RuntimeError("H1_EXTENSION_FREEZE_STATUS_MISMATCH")
    return d


def extension_schedule() -> dict[str, dict[str, str]]:
    return {r["date"]: {"WIN": r["WIN"], "WDO": r["WDO"]} for r in load_extension()["sessions"]}
