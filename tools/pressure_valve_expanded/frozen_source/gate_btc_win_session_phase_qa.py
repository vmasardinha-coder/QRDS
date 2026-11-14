"""Prospective source QA by B3 regular/call phase; never edits observed bars."""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json

CONTRACT_PATH = Path(__file__).parent / "gate_btc_factory" / "WIN_SESSION_PHASE_QA_20261015.v1.json"
CONTRACT_SHA256 = "60acbfd8ec94787e7b2f3143cf3df45c4a0d1910e9efc8dc4ff7cbc49074fd06"
TZ = ZoneInfo("America/Sao_Paulo")
POST_REGULAR_COUNT_FIX_EFFECTIVE_FROM = "2026-10-19"


def session_phase_qa(rows, session, expiration_local, max_window):
    raw = CONTRACT_PATH.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
        raise RuntimeError("SESSION_PHASE_CONTRACT_HASH_MISMATCH")
    c = json.loads(raw)
    day = date.fromisoformat(session)
    if datetime.fromisoformat(c["sealed_at_utc"].replace("Z", "+00:00")) >= datetime.fromisoformat(c["effective_from"] + "T09:00:00-03:00"):
        raise RuntimeError("SESSION_PHASE_CONTRACT_LATE_SEAL")
    times = [datetime.fromisoformat(row["timestamp"]).astimezone(TZ) for row in rows]
    legacy = all((b - a).total_seconds() == 300 for a, b in zip(times, times[1:]))
    receipt = {"contract_sha256": CONTRACT_SHA256, "effective_from": c["effective_from"], "historical_credit": 0, "observed_rows_mutated": False}
    if session < c["effective_from"]:
        return {**receipt, "policy": "LEGACY_FULL_SESSION_SPACING", "pass": legacy}
    expiry = date.fromisoformat(str(expiration_local))
    finish = c["expiry_regular_end"] if day == expiry else c["regular_end"]
    start = datetime.fromisoformat(session + "T" + c["regular_start"] + ":00").replace(tzinfo=TZ)
    end = datetime.fromisoformat(session + "T" + finish + ":00").replace(tzinfo=TZ)
    if int(max_window) + 120 + 5 >= (end - start).total_seconds() / 60:
        raise RuntimeError("FROZEN_OUTCOME_WINDOW_OUTSIDE_REGULAR_SESSION")
    expected = []
    t = start
    while t < end:
        expected.append(t)
        t += timedelta(minutes=5)
    normal = [t for t in times if start <= t < end]
    identity_ok = all(t.date() == day and t >= start and t.hour < 19 and t.minute % 5 == 0 and t.second == 0 for t in times)
    unique = len(times) == len(set(times)) and times == sorted(times)
    # The frozen contract separates regular-grid QA from call/post-regular bars.
    # Preserve decisions through 16/10; the correction applies prospectively only.
    legacy_post_count_ok = (session >= POST_REGULAR_COUNT_FIX_EFFECTIVE_FROM or
                            len(times) - len(normal) <= 1)
    valid = day.weekday() < 5 and expiry >= day and identity_ok and unique and normal == expected and legacy_post_count_ok
    return {**receipt, "policy": "B3_REGULAR_GRID_CALL_SEPARATE", "pass": valid,
            "regular_start": start.isoformat(), "regular_end_exclusive": end.isoformat(),
            "expected_regular_bars": len(expected), "observed_regular_bars": len(normal),
            "observed_call_or_post_regular_bars": len(times) - len(normal),
            "post_regular_count_fix_effective_from": POST_REGULAR_COUNT_FIX_EFFECTIVE_FROM,
            "post_regular_count_independent": session >= POST_REGULAR_COUNT_FIX_EFFECTIVE_FROM}

