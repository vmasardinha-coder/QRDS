"""Physical M5 holding window for an exit at the next bar's open."""
from datetime import datetime, timedelta
import math


def closed_holding_window(by_time: dict, entry_time: datetime, exit_time: datetime) -> list[dict]:
    # Exit is executed at exit_time.open. Its still-forming high/low cannot
    # belong to the position's excursion or change a previously written close.
    if exit_time - entry_time != timedelta(minutes=120):
        raise RuntimeError("H31_FROZEN_HOLD_DURATION_MISMATCH")
    times = [entry_time + timedelta(minutes=5*i) for i in range(24)]
    missing = [t.isoformat() for t in times if t not in by_time]
    if missing:
        raise RuntimeError("H31_INCOMPLETE_CLOSED_HOLD_WINDOW:" + ",".join(missing))
    rows = [by_time[t] for t in times]
    for timestamp,row in zip(times,rows):
        if datetime.fromisoformat(row["timestamp"]) != timestamp:
            raise RuntimeError("H31_HOLD_TIMESTAMP_MISMATCH")
        o,h,l,c = [float(row[k]) for k in ("open","high","low","close")]
        if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
            raise RuntimeError("H31_HOLD_PHYSICAL_OHLC_FAILED")
    return rows


def prior_close_hash(directory, event):
    """Keep prior closes immutable; auxiliary changes cannot append a trade."""
    import hashlib
    import json
    if event.get("event_type") != "PAPER_CLOSE":
        return None
    omitted = {"event_hash_sha256", "MAE_bps", "MFE_bps"}
    economic = {k:v for k,v in event.items() if k not in omitted}
    hashes = []
    for path in sorted(directory.glob("*.json")):
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior.get("event_type") != "PAPER_CLOSE":
            continue
        body = {k:v for k,v in prior.items() if k != "event_hash_sha256"}
        digest = hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        if prior.get("event_hash_sha256") != digest:
            raise RuntimeError("H31_EXISTING_CLOSE_HASH_MISMATCH")
        if {k:v for k,v in prior.items() if k not in omitted} != economic:
            raise RuntimeError("H31_CONFLICTING_ECONOMIC_CLOSE")
        hashes.append(digest)
    return hashes[0] if hashes else None
