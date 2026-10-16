"""Validate an append-only H31 excursion correction against physical bars."""
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

try:
    from tools.gate_btc_h31_close_window import closed_holding_window
except ModuleNotFoundError:
    from gate_btc_h31_close_window import closed_holding_window


def adjudicated_hashes(shadow_dir, session, closes):
    path=Path(shadow_dir)/"close_metric_adjudications"/(session+".json")
    if not path.exists():
        return set()
    receipt=json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "gate_btc.h31.closed_window_auxiliary_adjudication.v1" or receipt.get("session") != session:
        raise ValueError("invalid auxiliary adjudication identity")
    if receipt.get("canonical_credit") != 0 or receipt.get("events_rewritten") is not False:
        raise ValueError("auxiliary adjudication boundary violation")
    covered=set(receipt["close_event_hashes"])
    actual={digest for digest,event in closes.items() if event["session"]==session}
    if covered != actual or len(covered)<2:
        raise ValueError("auxiliary adjudication event set mismatch")
    events=[closes[digest] for digest in sorted(covered)]
    omit={"event_hash_sha256","MAE_bps","MFE_bps"}
    economics=[{k:v for k,v in event.items() if k not in omit} for event in events]
    if any(x!=economics[0] for x in economics):
        raise ValueError("financial disagreement cannot be adjudicated as auxiliary")
    economic=economics[0]
    if economic != receipt["economic_payload"]:
        raise ValueError("adjudication financial payload mismatch")
    raw=receipt["physical_window"]
    digest=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if digest != receipt["physical_window_digest"]:
        raise ValueError("physical holding window hash mismatch")
    entry_time=datetime.fromisoformat(economic["entry_timestamp"])
    exit_time=datetime.fromisoformat(economic["exit_timestamp"])
    if len(raw["bars"])!=24 or len({x["timestamp"] for x in raw["bars"]})!=24:
        raise ValueError("auxiliary physical window must have 24 distinct bars")
    rows={datetime.fromisoformat(x["timestamp"]):x for x in raw["bars"]}
    hold=closed_holding_window(rows,entry_time,exit_time)
    entry=float(economic["entry"]);exit_=float(economic["exit"]);side=economic["side"]
    if hold[0]["open"]!=entry or raw["exit_open"]!=exit_ or side not in (-1,1):
        raise ValueError("entry/exit physical source mismatch")
    gross=side*(exit_/entry-1)*10000
    if not math.isclose(gross,economic["gross_bps"],rel_tol=0,abs_tol=1e-9):
        raise ValueError("financial return mismatch")
    if side>0:
        mae=(min(x["low"] for x in hold)/entry-1)*10000
        mfe=(max(x["high"] for x in hold)/entry-1)*10000
    else:
        mae=(entry/max(x["high"] for x in hold)-1)*10000
        mfe=(entry/min(x["low"] for x in hold)-1)*10000
    if not math.isclose(mae,receipt["corrected_MAE_bps"],rel_tol=0,abs_tol=1e-9) or not math.isclose(mfe,receipt["corrected_MFE_bps"],rel_tol=0,abs_tol=1e-9):
        raise ValueError("auxiliary corrected metric mismatch")
    # The legacy bug includes the exit bar: its extrema can only widen excursion.
    if any(x["MFE_bps"]<mfe-1e-9 or x["MAE_bps"]>mae+1e-9 for x in events):
        raise ValueError("legacy excursions are not explained by the exit-bar defect")
    return covered
