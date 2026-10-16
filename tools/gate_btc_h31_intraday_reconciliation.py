"""Read-only reconciliation of H31 trigger decisions and causal closes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from tools.gate_btc_h31_auxiliary_adjudication import adjudicated_hashes
except ModuleNotFoundError:
    from gate_btc_h31_auxiliary_adjudication import adjudicated_hashes


def event_digest(event: dict) -> str:
    payload = {k: v for k, v in event.items() if k != "event_hash_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def reconcile_intraday_events(shadow_dir: Path) -> dict:
    decisions: dict[str, dict] = {}
    closes: dict[str, dict] = {}
    invalid: list[str] = []
    root = shadow_dir / "intraday_events"
    for path in sorted(root.glob("*/*.json")):
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
            digest = event_digest(event)
            if event.get("event_hash_sha256") != digest or event.get("session") != path.parent.name:
                raise ValueError("event identity mismatch")
            kind = event.get("event_type")
            if kind == "DECISION":
                old = decisions.get(event["session"])
                if old is not None and event_digest(old) != digest:
                    raise ValueError("conflicting decisions")
                decisions[event["session"]] = event
            elif kind == "PAPER_CLOSE":
                closes[digest] = event
        except (ValueError, TypeError, KeyError):
            invalid.append(str(path.relative_to(root)))
    triggered = {session: event for session, event in decisions.items() if event.get("trigger_state") == "TRIGGER"}
    adjudicated=set()
    for session in sorted({x["session"] for x in closes.values()}):
        try:
            adjudicated.update(adjudicated_hashes(shadow_dir,session,closes))
        except (ValueError,TypeError,KeyError,RuntimeError) as exc:
            invalid.append("invalid_auxiliary_adjudication:"+session+":"+str(exc))
    adjudicated_variants=0
    closed: dict[str, str] = {}
    for digest, close in closes.items():
        session = close["session"]
        decision = triggered.get(session)
        if decision is None or close.get("decision_hash") != event_digest(decision):
            invalid.append("orphan_close:" + digest)
        elif session in closed:
            if digest in adjudicated and closed[session] in adjudicated:
                adjudicated_variants+=1
            else:
                invalid.append("conflicting_close:" + session)
        else:
            closed[session] = digest
    missing = sorted(set(triggered) - set(closed))
    quality = "FAIL_EVENT_RECONCILIATION" if invalid else ("PARTIAL_UNCLOSED_TRIGGER_GAPS" if missing else "PASS_TRIGGER_CLOSE_RECONCILIATION")
    return {
        "H31_SHADOW_TRIGGERED_SESSIONS": len(triggered),
        "H31_SHADOW_CLOSED_TRADES": len(closed),
        "H31_SHADOW_TRIGGER_SESSIONS_WITHOUT_CLOSE": missing,
        "H31_SHADOW_CLOSE_RECONCILIATION_STATUS": quality,
        "H31_SHADOW_INVALID_EVENT_COUNT": len(invalid),
        "H31_SHADOW_ADJUDICATED_AUXILIARY_VARIANT_COUNT": adjudicated_variants,
        "H31_SHADOW_ORIGINAL_EVENT_FILES_PRESERVED": True,
        "H31_SHADOW_INVALID_EVENT_REASONS": sorted(invalid),
        "H31_SHADOW_SIMULATED_TRADES_SEMANTICS": "TRIGGER_DECISIONS_NOT_CLOSED_RETURNS",
    }
