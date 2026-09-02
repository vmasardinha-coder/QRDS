#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")


def arg_value(name: str, default: str) -> str:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def has_decision(shadow_dir: Path, session: str) -> bool:
    root = shadow_dir / "intraday_events" / session
    if not root.exists():
        return False
    for p in root.glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("event_type") == "DECISION":
            return True
    return False


def persist_missed_window(shadow_dir: Path, session: str, now: datetime) -> None:
    p = shadow_dir / "INTRADAY_STATUS.json"
    status = {}
    if p.exists():
        try:
            status = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            status = {}
    status.update({
        "schema": "gate_btc.b3.h31.intraday_shadow_status.v1",
        "H31_INTRADAY_SHADOW_STATUS": "ACTIVE",
        "H31_INTRADAY_SESSION": session,
        "H31_INTRADAY_MONITORING": False,
        "H31_30M_WINDOW_COMPLETE": True,
        "H31_TRIGGER_STATE": "PENDING",
        "H31_PAPER_POSITION": "NONE",
        "H31_MT5_READY": False,
        "monitor_error": "MISSED_CAUSAL_WINDOW_NO_BACKFILL",
        "NO_BACKFILL": True,
        "NO_RETUNE": True,
        "SHADOW_ONLY": True,
        "MT5_READ_ONLY": True,
        "PAPER_CALCULATION": True,
        "NO_ORDER_SEND": True,
        "CANONICAL_PROSPECTIVE_CREDIT": 0,
        "SCIENTIFIC_PROMOTION_CREDIT": 0,
        "SHADOW_CREDIT_TO_CANONICAL": 0,
        "CANONICAL_COUNTER_CHANGED": False,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "updated_at": now.isoformat(),
    })
    shadow_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(status, sort_keys=True))


def main() -> int:
    shadow_dir = Path(arg_value("--shadow-dir", "runtime/ledgers/b3_h31_shadow_paper"))
    now = datetime.now(TZ)
    session = now.date().isoformat()
    window_end = datetime(now.year, now.month, now.day, 9, 30, tzinfo=TZ)
    first_scheduled_post_window = window_end + timedelta(minutes=5)

    # NO_BACKFILL: a new same-day decision may only be born in the first
    # scheduled five-minute slot after the frozen 30m signal window closes.
    # Existing decisions may continue to be monitored/closed later in-session.
    if now > first_scheduled_post_window and not has_decision(shadow_dir, session):
        persist_missed_window(shadow_dir, session, now)
        return 2

    cmd = [sys.executable, "tools/gate_btc_b3_h31_intraday_shadow.py", *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
