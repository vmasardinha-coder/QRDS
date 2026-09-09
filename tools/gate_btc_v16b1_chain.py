#!/usr/bin/env python3
"""Append-only staged seals for V16B.1-OKX.

Stages: V16B1_SIGNAL_SEAL -> V16B1_ENTRY_SEAL -> V16B1_RESULT_SEAL -> optional
external Delta attachment. The original V16B ledger/counter is never reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

CANDIDATE_ID = "GATE_BTC_V16B1_OKX_CORE"
FIRST_SIGNAL = date(2026, 9, 17)
FIRST_ENTRY = date(2026, 9, 18)
FIRST_COMPLETE_EXIT = date(2026, 9, 25)
COST_BPS = 15.0
TOL = 1e-9
SAFETY = {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True, "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0}

SIGNAL_REQUIRED = {
    "signal_date_utc","entry_date_utc","candidate_id","model_hash","code_commit","input_data_hashes",
    "universe_snapshot_id","universe_snapshot_available_at_utc","panel_hash","model_state_hash",
    "eligible_universe_count","liquidity_qualified_count","eligible_scores","long_ranking_desc","short_ranking_asc",
    "preliminary_longs_10","risk_state","source_coverage","status","blocker_reason",
}
ENTRY_REQUIRED = {
    "signal_date_utc","entry_date_utc","candidate_id","signal_seal_sha256","shortability_evidence_hash",
    "shortability_checked_ranked","long_executability","longs_10","shorts_10","entry_instruments","exposure",
    "trailing_vol","turnover_estimate","transaction_cost_bps","source_coverage","status","blocker_reason",
}
RESULT_REQUIRED = {
    "signal_date_utc","entry_date_utc","exit_date_utc","candidate_id","entry_seal_sha256","execution_ledger_hash",
    "price_source_hashes","per_asset_pnl","transaction_cost","short_funding","funding_evidence_hash",
    "gross_long_pnl","gross_short_pnl","net_pnl","btc_benchmark_return","btc_entry_price","btc_exit_price",
    "btc_source_hash","source_coverage","status","blocker_reason",
}


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def _parse_date(v: str) -> date:
    return date.fromisoformat(v)


def _parse_utc(v: str) -> datetime:
    dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def _close_after_day(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _event_time(now: datetime | None) -> datetime:
    x = now or datetime.now(timezone.utc)
    if x.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return x.astimezone(timezone.utc)


def _require_hash(v: Any, name: str, length: int = 64) -> None:
    if not isinstance(v, str) or len(v) != length or any(c not in "0123456789abcdefABCDEF" for c in v):
        raise ValueError(f"{name} must be a {length}-hex string")


def _require_fields(row: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - row.keys())
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    if row.get("candidate_id") != CANDIDATE_ID:
        raise ValueError("unexpected V16B.1 candidate_id")
    if "external_delta_print" in row or "external_delta" in row:
        raise ValueError("external Delta forbidden before RESULT seal")


def _status(row: dict[str, Any]) -> str:
    status = row.get("status")
    if status not in {"OK", "BLOCKED"}:
        raise ValueError("status must be OK or BLOCKED")
    if status == "OK" and row.get("blocker_reason") not in (None, ""):
        raise ValueError("OK row cannot carry blocker_reason")
    if status == "BLOCKED" and not row.get("blocker_reason"):
        raise ValueError("BLOCKED row requires blocker_reason")
    return status


def _stamp(row: dict[str, Any], event_type: str, created: datetime) -> dict[str, Any]:
    event = dict(row)
    event.update(SAFETY)
    event["event_type"] = event_type
    event["event_created_at_utc"] = created.isoformat().replace("+00:00", "Z")
    event["seal_sha256"] = sha256_obj({k: event[k] for k in sorted(event) if k != "seal_sha256"})
    return event


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def _unique(events: list[dict[str, Any]], event_type: str, signal_date: str) -> dict[str, Any]:
    rows = [e for e in events if e.get("event_type") == event_type and e.get("signal_date_utc") == signal_date]
    if len(rows) != 1:
        raise ValueError(f"requires exactly one {event_type} for {signal_date}")
    return rows[0]


def validate_signal_row(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, SIGNAL_REQUIRED)
    signal, entry = _parse_date(row["signal_date_utc"]), _parse_date(row["entry_date_utc"])
    if signal < FIRST_SIGNAL or entry < FIRST_ENTRY or signal.weekday() != 3 or entry != signal + timedelta(days=1):
        raise ValueError("invalid/pre-family V16B.1 weekly clock")
    created = _event_time(now)
    if not (_close_after_day(signal) <= created < _close_after_day(entry)):
        raise ValueError("V16B.1 SIGNAL seal outside causal window")
    for name, length in (("model_hash",64),("code_commit",40),("panel_hash",64),("model_state_hash",64)):
        _require_hash(row[name], name, length)
    if not isinstance(row["input_data_hashes"], dict) or not row["input_data_hashes"]:
        raise ValueError("input_data_hashes required")
    for k, v in row["input_data_hashes"].items():
        _require_hash(v, f"input_data_hashes[{k}]")
    if _parse_utc(row["universe_snapshot_available_at_utc"]) > _close_after_day(signal):
        raise ValueError("late universe snapshot")
    status = _status(row)
    if status == "OK":
        scores = row["eligible_scores"]
        lr, sr, longs = row["long_ranking_desc"], row["short_ranking_asc"], row["preliminary_longs_10"]
        if not isinstance(scores, dict) or len(scores) < 20:
            raise ValueError("OK SIGNAL requires >=20 scores")
        if set(lr) != set(scores) or set(sr) != set(scores) or len(lr) != len(set(lr)) or len(sr) != len(set(sr)):
            raise ValueError("rankings must uniquely cover eligible_scores")
        lv = [float(scores[a]) for a in lr]; sv = [float(scores[a]) for a in sr]
        if any(lv[i] + TOL < lv[i+1] for i in range(len(lv)-1)):
            raise ValueError("long ranking not descending")
        if any(sv[i] > sv[i+1] + TOL for i in range(len(sv)-1)):
            raise ValueError("short ranking not ascending")
        if longs != lr[:10]:
            raise ValueError("preliminary longs must equal top 10")
        risk = row["risk_state"]
        if not isinstance(risk, dict) or not 0 < float(risk["exposure"]) <= 1:
            raise ValueError("invalid risk_state")
    return _stamp(row, "V16B1_SIGNAL_SEAL", created)


def validate_entry_row(row: dict[str, Any], signal_event: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, ENTRY_REQUIRED)
    if row["signal_seal_sha256"] != signal_event["seal_sha256"]:
        raise ValueError("signal seal hash mismatch")
    if row["signal_date_utc"] != signal_event["signal_date_utc"] or row["entry_date_utc"] != signal_event["entry_date_utc"]:
        raise ValueError("entry dates mismatch")
    created = _event_time(now)
    entry = _parse_date(row["entry_date_utc"])
    if created < _parse_utc(signal_event["event_created_at_utc"]) or created >= _close_after_day(entry):
        raise ValueError("V16B.1 ENTRY seal outside causal window")
    _require_hash(row["shortability_evidence_hash"], "shortability_evidence_hash")
    status = _status(row)
    if status == "OK":
        if signal_event["status"] != "OK":
            raise ValueError("cannot create OK ENTRY from blocked SIGNAL")
        longs, shorts = row["longs_10"], row["shorts_10"]
        if longs != signal_event["preliminary_longs_10"] or len(longs) != 10 or len(shorts) != 10:
            raise ValueError("entry holdings cardinality/frozen longs mismatch")
        if set(longs) & set(shorts):
            raise ValueError("long/short overlap")
        checked = row["shortability_checked_ranked"]
        selected = []
        for i, item in enumerate(checked):
            if item.get("asset") != signal_event["short_ranking_asc"][i] or "shortable" not in item or not item.get("evidence_ref"):
                raise ValueError("short checks must follow frozen ascending rank")
            if item["shortable"]:
                selected.append(item["asset"])
                if len(selected) == 10:
                    if i != len(checked)-1:
                        raise ValueError("checks must stop at 10th short")
                    break
        if selected != shorts:
            raise ValueError("shorts must equal first 10 causal OKX-admissible assets")
        instruments = row["entry_instruments"]
        if set(instruments) != set(longs) | set(shorts):
            raise ValueError("entry instruments must cover exact holdings")
        if any(not str(instruments[a]).startswith("BINANCE_SPOT|") for a in longs):
            raise ValueError("long instrument venue mismatch")
        if any(not str(instruments[a]).startswith("OKX_SWAP|") for a in shorts):
            raise ValueError("short instrument venue mismatch")
        if abs(float(row["transaction_cost_bps"]) - COST_BPS) > TOL:
            raise ValueError("primary transaction cost must remain 15 bps")
    return _stamp(row, "V16B1_ENTRY_SEAL", created)


def validate_result_row(row: dict[str, Any], entry_event: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, RESULT_REQUIRED)
    signal, entry, exit_ = map(_parse_date, (row["signal_date_utc"], row["entry_date_utc"], row["exit_date_utc"]))
    if signal < FIRST_SIGNAL or entry < FIRST_ENTRY or exit_ < FIRST_COMPLETE_EXIT or exit_ != entry + timedelta(days=7):
        raise ValueError("invalid V16B.1 result clock")
    if row["entry_seal_sha256"] != entry_event["seal_sha256"]:
        raise ValueError("entry seal hash mismatch")
    created = _event_time(now)
    if created < _close_after_day(exit_):
        raise ValueError("result cannot seal before exit-day UTC close")
    status = _status(row)
    if status == "OK":
        if entry_event["status"] != "OK":
            raise ValueError("cannot create OK RESULT from blocked ENTRY")
        for h in ("execution_ledger_hash","funding_evidence_hash","btc_source_hash"):
            _require_hash(row[h], h)
        expected = set(entry_event["longs_10"]) | set(entry_event["shorts_10"])
        details = row["per_asset_pnl"]
        if not isinstance(details, list) or len(details) != 20 or {x["asset"] for x in details} != expected:
            raise ValueError("per_asset_pnl must cover exact 20 holdings")
        long_sum = short_sum = 0.0
        exposure = float(entry_event["exposure"])
        for item in details:
            asset = item["asset"]
            side = "LONG" if asset in entry_event["longs_10"] else "SHORT"
            if item["side"] != side or item["instrument"] != entry_event["entry_instruments"][asset]:
                raise ValueError("result side/instrument mismatch")
            ep, xp = float(item["entry_price"]), float(item["exit_price"])
            raw = xp/ep - 1.0
            weight = 0.05 * exposure * (1 if side == "LONG" else -1)
            if abs(float(item["raw_return"]) - raw) > 1e-8 or abs(float(item["weight"]) - weight) > 1e-10:
                raise ValueError("result return/weight mismatch")
            wpnl = weight * raw
            if abs(float(item["weighted_pnl"]) - wpnl) > 1e-8:
                raise ValueError("weighted pnl mismatch")
            _require_hash(item["price_source_hash"], "price_source_hash")
            if side == "LONG": long_sum += wpnl
            else: short_sum += wpnl
        funding = row["short_funding"]
        if not isinstance(funding, dict) or set(funding) != set(entry_event["shorts_10"]):
            raise ValueError("short_funding must cover exact shorts")
        cost = COST_BPS/10000.0 * float(entry_event["turnover_estimate"])
        if abs(float(row["transaction_cost"]) - cost) > 1e-10:
            raise ValueError("transaction cost mismatch")
        net = long_sum + short_sum + sum(float(v) for v in funding.values()) - cost
        if abs(float(row["gross_long_pnl"]) - long_sum) > 1e-8 or abs(float(row["gross_short_pnl"]) - short_sum) > 1e-8 or abs(float(row["net_pnl"]) - net) > 1e-8:
            raise ValueError("aggregate PnL mismatch")
        if abs(float(row["btc_benchmark_return"]) - (float(row["btc_exit_price"])/float(row["btc_entry_price"])-1)) > 1e-8:
            raise ValueError("BTC benchmark mismatch")
    return _stamp(row, "V16B1_RESULT_SEAL", created)


def derive_stress_children(result_event: dict[str, Any], entry_event: dict[str, Any]) -> list[dict[str, Any]]:
    if result_event.get("event_type") != "V16B1_RESULT_SEAL" or result_event.get("status") != "OK":
        raise ValueError("stress children require sealed OK CORE result")
    pre_cost = float(result_event["gross_long_pnl"]) + float(result_event["gross_short_pnl"]) + sum(float(v) for v in result_event["short_funding"].values())
    turnover = float(entry_event["turnover_estimate"])
    out = []
    for bps, child in ((30.0,"GATE_BTC_V16B1_OKX_COST30_STRESS"),(50.0,"GATE_BTC_V16B1_OKX_COST50_STRESS")):
        cost = bps/10000.0 * turnover
        row = {
            "event_type": "V16B1_STRESS_CHILD",
            "child_id": child,
            "parent_candidate_id": CANDIDATE_ID,
            "signal_date_utc": result_event["signal_date_utc"],
            "result_seal_sha256": result_event["seal_sha256"],
            "same_holdings_as_core": True,
            "transaction_cost_bps": bps,
            "transaction_cost": cost,
            "net_pnl": pre_cost - cost,
            "selection_power": False,
            **SAFETY,
        }
        row["seal_sha256"] = sha256_obj({k: row[k] for k in sorted(row) if k != "seal_sha256"})
        out.append(row)
    return out


def seal(kind: str, input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    events = load_events(ledger)
    if kind == "signal":
        event = validate_signal_row(row, now)
        et = "V16B1_SIGNAL_SEAL"
    elif kind == "entry":
        sig = _unique(events, "V16B1_SIGNAL_SEAL", row.get("signal_date_utc", ""))
        event = validate_entry_row(row, sig, now)
        et = "V16B1_ENTRY_SEAL"
    else:
        ent = _unique(events, "V16B1_ENTRY_SEAL", row.get("signal_date_utc", ""))
        event = validate_result_row(row, ent, now)
        et = "V16B1_RESULT_SEAL"
    if any(e.get("event_type") == et and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("append-only ledger forbids replacement")
    append_jsonl(ledger, event)
    return event


def main() -> int:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    for cmd in ("seal-signal","seal-entry","seal-result"):
        q=sub.add_parser(cmd); q.add_argument("--input",required=True); q.add_argument("--ledger",required=True)
    a=p.parse_args(); kind=a.cmd.removeprefix("seal-")
    event=seal(kind,Path(a.input),Path(a.ledger))
    print(json.dumps({"status":"PASS","event_type":event["event_type"],"seal_sha256":event["seal_sha256"],"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
