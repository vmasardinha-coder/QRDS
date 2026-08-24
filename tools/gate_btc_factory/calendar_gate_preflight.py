#!/usr/bin/env python3
"""Fail-closed, reporting-only preflight for calendar-gated shadow tracks.

No strategy economics are read or modified. The script only validates frozen runtime
status contracts and readiness dates. It is intentionally conservative: any missing
status, malformed date, safety-boundary breach, or unexpected clock becomes RED.
"""
from __future__ import annotations
import argparse, json, pathlib, sys
from datetime import date, datetime

SAFETY_DEFAULTS = {
    "research_only": True,
    "not_approved": True,
}

TRACKS = {
    "qos_monthly": {
        "path": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
        "expected_first": "2026-08-31",
        "mode": "measurement_qos",
    },
    "prl50": {
        "path": "runtime/ledgers/prl50_position/STATUS.json",
        "expected_first": "2026-08-31",
        "mode": "status_signal",
    },
    "alt_trail": {
        "path": "runtime/ledgers/alt_trail40_10/STATUS.json",
        "expected_first": "2026-08-31",
        "expected_execution": "2026-09-01",
        "mode": "status_signal_execution",
    },
    "v16b": {
        "path": "runtime/ledgers/v16b/STATUS.json",
        "expected_first": "2026-08-27",
        "mode": "v16b",
    },
}

def load_json(root: pathlib.Path, rel: str):
    p = root / rel
    if not p.is_file():
        raise FileNotFoundError(rel)
    return json.loads(p.read_text(encoding="utf-8")), p

def assert_safety(obj: dict, name: str):
    # Accept explicit false-zero forms but never a positive order/capital authorization.
    for k in ("orders", "orders_generated", "real_orders"):
        if k in obj and obj[k] not in (0, None):
            raise ValueError(f"{name}: {k} must remain 0")
    for k in ("capital", "real_capital_used", "capital_used"):
        if k in obj and obj[k] not in (0, 0.0, None):
            raise ValueError(f"{name}: {k} must remain 0")
    if obj.get("not_approved") is False or obj.get("operational_status") == "APPROVED":
        raise ValueError(f"{name}: approval boundary breached")
    if obj.get("engine_feed") is True:
        raise ValueError(f"{name}: engine_feed must remain false")

def parse_day(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def check(root: pathlib.Path, today: date):
    rows=[]
    for name,cfg in TRACKS.items():
        try:
            obj,p=load_json(root,cfg["path"])
            assert_safety(obj,name)
            first=parse_day(cfg["expected_first"])
            days=(first-today).days
            if cfg["mode"] == "measurement_qos":
                qos_monthly=obj.get("qos_monthly")
                if not isinstance(qos_monthly, dict):
                    raise ValueError("canonical qos_monthly object missing from measurement status")
                expected=qos_monthly.get("expected_closes")
                if not isinstance(expected, list):
                    raise ValueError("canonical qos_monthly.expected_closes missing or malformed")
                if cfg["expected_first"] not in expected:
                    raise ValueError("frozen 2026-08-31 QOS close missing from qos_monthly.expected_closes")
            elif cfg["mode"] == "status_signal":
                if obj.get("first_eligible_signal_date") != cfg["expected_first"]:
                    raise ValueError("unexpected first eligible signal date")
            elif cfg["mode"] == "status_signal_execution":
                if obj.get("first_eligible_signal_date") != cfg["expected_first"]:
                    raise ValueError("unexpected first eligible signal date")
                if obj.get("first_eligible_execution_date") != cfg["expected_execution"]:
                    raise ValueError("unexpected first eligible execution date")
            elif cfg["mode"] == "v16b":
                if obj.get("canonical_cycle_count", 0) < 0:
                    raise ValueError("invalid canonical cycle count")
                if obj.get("next_canonical_event") not in ("SIGNAL_2026-08-27", None):
                    raise ValueError("unexpected V16B next canonical event")
            phase="D-2" if days==2 else "D-1" if days==1 else "CLOCK" if days==0 else f"D{days:+d}"
            rows.append({"track":name,"status":"PASS_PREFLIGHT","phase":phase,"source":str(p),"days_to_first_clock":days})
        except Exception as e:
            rows.append({"track":name,"status":"RED_FAIL_CLOSED","error":str(e)})
    overall="PASS" if all(r["status"]=="PASS_PREFLIGHT" for r in rows) else "RED_FAIL_CLOSED"
    return {"schema":"gate_btc.calendar_gate_preflight.v1","generated_at_utc":datetime.utcnow().isoformat(timespec="seconds")+"Z","today_utc":today.isoformat(),"overall_status":overall,"rows":rows,"research_only":True,"shadow_only":True,"not_approved":True,"orders":0,"real_capital":0,"engine_feed":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--runtime-root",required=True)
    ap.add_argument("--today",default=date.today().isoformat())
    ap.add_argument("--output",default="calendar_gate_preflight_status.json")
    args=ap.parse_args()
    result=check(pathlib.Path(args.runtime_root),parse_day(args.today))
    pathlib.Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["overall_status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
