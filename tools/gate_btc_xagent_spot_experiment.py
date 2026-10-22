"""Isolated prospective disagreement experiment; never changes the parent handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from gate_btc_factory.xagent_disagree_transform import transform

CONTRACT = Path(__file__).resolve().parent / "gate_btc_factory/XAGENT_SPOT_CONTINUOUS_V1.json"
CONTRACT_SHA256 = "d2cdb0cd567213d24d4e32c6d27f3435a8bf1bd32e7288861cf5fc3b7bea4d2c"
LANE = Path("factory_autonomy/xagent_economics/F-XAGENT-DISAGREE-SPOT-CONTINUOUS-V1")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def seal(d):
    return {**d, "record_sha256": digest(canonical(d))}


def verify(d):
    raw = {k: v for k, v in d.items() if k != "record_sha256"}
    if d.get("record_sha256") != digest(canonical(raw)):
        raise ValueError("RECORD_HASH_MISMATCH")
    return d


def load_contract():
    raw = CONTRACT.read_bytes()
    if digest(raw) != CONTRACT_SHA256:
        raise ValueError("CONTRACT_HASH_MISMATCH")
    c = json.loads(raw)
    if timestamp(c["preregistered_at_utc"]) >= timestamp(c["first_decision_date_utc"] + "T02:00:00Z"):
        raise ValueError("CONTRACT_NOT_EX_ANTE")
    return c


def timestamp(s):
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return t.astimezone(timezone.utc)


def immutable(path, d):
    raw = json.dumps(d, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("IMMUTABLE_RECORD_CONFLICT:" + path.name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(raw); tmp.replace(path)


def make_decision(records, now, runtime_sha, c):
    day = now.date().isoformat()
    start = timestamp(day + "T" + c["decision_window_utc"][0] + "Z")
    end = timestamp(day + "T" + c["decision_window_utc"][1] + "Z")
    if day < c["first_decision_date_utc"] or not start <= now <= end:
        raise ValueError("OUTSIDE_PREREGISTERED_DECISION_WINDOW")
    errors = []
    by_id = {}
    for r in records:
        pid = r.get("producer_id")
        if pid in by_id or pid not in c["producers"]:
            raise ValueError("DUPLICATE_OR_UNDECLARED_PRODUCER")
        verify(r)
        if r.get("schema") != "gate_btc_2.xagent_signal_observation.v1" or r.get("evidence_class") != c["producers"][pid]:
            raise ValueError("PRODUCER_CONTRACT_MISMATCH")
        age = now.timestamp() - float(r["available_after_ms"]) / 1000
        if age < 0 or age > c["input_max_age_seconds"]:
            errors.append(pid + ":STALE_OR_FUTURE")
        if pid == "S-XSPOT-FLOW-01" and (r.get("instrument") != "BTCUSDT"
                or r.get("source_checks", {}).get("closed_kline") is not True
                or float(r.get("close_time_ms", float("inf"))) > float(r["available_after_ms"])):
            raise ValueError("SPOT_SOURCE_CAUSALITY_INVALID")
        if pid == "S-XBREADTH-01" and (float(r.get("common_closed_bar_close_ms", float("inf")))
                                      > float(r["available_after_ms"])):
            raise ValueError("BREADTH_SOURCE_CAUSALITY_INVALID")
        if pid == "S-XTERM-CARRY-01" and float(r.get("capture_time_ms", float("inf"))) > float(r["available_after_ms"]):
            raise ValueError("CARRY_SOURCE_CAUSALITY_INVALID")
        if (r.get("economic_outcomes_read") is not False or r.get("engine_feed") is not False
                or r.get("orders") != 0 or r.get("real_capital") != 0):
            raise ValueError("PRODUCER_SAFETY_CHANGED")
        by_id[pid] = r
    if set(by_id) != set(c["producers"]):
        errors.append("REQUIRED_PRODUCER_MISSING")
    vector = transform(records)
    if vector["available_count"] != 3:
        errors.append("REQUIRED_SIGNAL_UNAVAILABLE")
    eligible = not errors
    f = vector.get("features") or {}
    base = max(0.0, f["consensus_mean"]) if eligible else None
    weight = base * (1 - f["pairwise_disagreement"]) if eligible else None
    entry = timestamp(day + "T" + c["entry_time_utc"] + "Z")
    return seal({"schema": "qrds.xagent_spot_decision.v1", "experiment_id": c["experiment_id"],
                 "day": day, "decision_at_utc": now.isoformat(), "entry_at_utc": entry.isoformat(),
                 "exit_at_utc": (entry + timedelta(hours=c["horizon_hours"])).isoformat(),
                 "contract_sha256": CONTRACT_SHA256, "source_runtime_sha": runtime_sha,
                 "input_record_hashes": {p: r["record_sha256"] for p, r in sorted(by_id.items())},
                 "status": "DECISION_READY" if eligible else "ABSTAIN_INPUT_UNAVAILABLE",
                 "reasons": errors, "features": f if eligible else None,
                 "consensus_weight": base, "candidate_weight": weight, "safety": c["safety"]})


def event_return(weight, ratio, cost_bps):
    if not 0 <= weight <= 1 or not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("INVALID_EXPOSURE_OR_PRICE_RATIO")
    c = cost_bps / 10000
    return (1 - weight) + weight / (1 + c) * ratio * (1 - c) - 1


def outcome(d, entry, exit_, now, proof, c):
    verify(d)
    if d["status"] != "DECISION_READY" or d["contract_sha256"] != CONTRACT_SHA256:
        raise ValueError("DECISION_NOT_ELIGIBLE")
    begin, end = timestamp(d["entry_at_utc"]), timestamp(d["exit_at_utc"])
    if end - begin != timedelta(hours=c["horizon_hours"]):
        raise ValueError("FROZEN_HORIZON_CHANGED")
    if now < end + timedelta(minutes=1):
        raise ValueError("OUTCOME_NOT_MATURE")
    if proof["decision_record_sha256"] != d["record_sha256"] or timestamp(proof["commit_at_utc"]) >= begin:
        raise ValueError("DECISION_NOT_PUBLISHED_BEFORE_ENTRY")
    for row, target in [(entry, begin), (exit_, end)]:
        if int(row[0]) != int(target.timestamp() * 1000) or int(row[6]) >= int(now.timestamp() * 1000):
            raise ValueError("EXACT_CLOSED_PRICE_MINUTE_REQUIRED")
        prices = [float(row[i]) for i in (1, 2, 3, 4)]
        op, high, low, close = prices
        if (any(not math.isfinite(x) or x <= 0 for x in prices) or low > min(op, close)
                or high < max(op, close) or low > high):
            raise ValueError("PRICE_OHLC_INVALID")
    ratio = float(exit_[1]) / float(entry[1])
    ref, stress = c["reference_cost_bps_per_side"], c["stress_cost_bps_per_side"]
    candidate = event_return(d["candidate_weight"], ratio, ref)
    base = event_return(d["consensus_weight"], ratio, ref)
    return seal({"schema": "qrds.xagent_spot_outcome.v1", "day": d["day"],
                 "decision_record_sha256": d["record_sha256"], "contract_sha256": CONTRACT_SHA256,
                 "source_seal": proof, "entry_candle": entry, "exit_candle": exit_,
                 "btc_gross_return": ratio - 1, "btc_paired_roundtrip_net": event_return(1, ratio, ref),
                 "cash_return": 0, "candidate_net": candidate, "consensus_net": base,
                 "primary_excess_net": candidate - base,
                 "candidate_stress_net": event_return(d["candidate_weight"], ratio, stress),
                 "paired_observation": 1, "safety": c["safety"]})


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if p.returncode:
        raise ValueError("SEALED_GIT_EVIDENCE_UNAVAILABLE")
    return p.stdout


def publication_proof(repo, decision_path, d, sha):
    if len(sha) != 40 or any(x not in "0123456789abcdef" for x in sha):
        raise ValueError("INVALID_PUBLICATION_SHA")
    try:
        raw = git(repo, "show", sha + ":" + decision_path.relative_to(repo).as_posix())
    except ValueError:
        git(repo, "fetch", "--depth=1", "origin", sha)
        raw = git(repo, "show", sha + ":" + decision_path.relative_to(repo).as_posix())
    if raw != decision_path.read_bytes():
        raise ValueError("PUBLISHED_DECISION_BYTES_DIFFER")
    committed = git(repo, "show", "-s", "--format=%cI", sha).decode().strip()
    if (timestamp(committed) >= timestamp(d["entry_at_utc"])
            or timestamp(committed) + timedelta(seconds=1) < timestamp(d["decision_at_utc"])):
        raise ValueError("DECISION_NOT_PUBLISHED_BEFORE_ENTRY")
    return {"commit_sha": sha, "commit_at_utc": committed, "decision_record_sha256": d["record_sha256"]}


def candle(c, at):
    ms = int(timestamp(at).timestamp() * 1000)
    params = {"symbol": c["instrument"], "interval": "1m", "startTime": ms, "endTime": ms + 59999, "limit": 1}
    with urlopen(c["price_endpoint"] + "?" + urlencode(params), timeout=20) as response:
        rows = json.load(response)
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("EXACT_PRICE_UNAVAILABLE")
    return rows[0]


def run(repo, now, acknowledge_sha=None):
    c = load_contract(); runtime = repo / "runtime"; lane = runtime / LANE
    changed_decision = None
    if acknowledge_sha:
        p = lane / "decisions" / (now.date().isoformat() + ".json")
        d = verify(json.loads(p.read_text()))
        immutable(lane / "seals" / p.name, publication_proof(repo, p, d, acknowledge_sha))
        return {"status": "PUBLICATION_SEAL_RECORDED"}
    blocked = []
    for p in sorted((lane / "decisions").glob("*.json")):
        target = lane / "outcomes" / p.name
        d = verify(json.loads(p.read_text()))
        if target.exists():
            verify(json.loads(target.read_text())); continue
        if d["status"] != "DECISION_READY" or now < timestamp(d["exit_at_utc"]) + timedelta(minutes=1):
            continue
        try:
            ack = json.loads((lane / "seals" / p.name).read_text())
            proof = publication_proof(repo, p, d, ack["commit_sha"])
            result = outcome(d, candle(c, d["entry_at_utc"]), candle(c, d["exit_at_utc"]), now, proof, c)
            immutable(target, result)
        except Exception as exc:
            blocked.append({"day": d["day"], "reason": type(exc).__name__ + ":" + str(exc)[:180]})
    path = lane / "decisions" / (now.date().isoformat() + ".json")
    if (now.date().isoformat() >= c["first_decision_date_utc"] and now.hour == 2
            and now.minute <= 45 and not path.exists()):
        records = []
        for pid in c["producers"]:
            source = runtime / "factory_autonomy/xagent_signal_producers" / pid / "LATEST.json"
            if source.exists():
                records.append(json.loads(source.read_text()))
        d = make_decision(records, now, git(repo, "rev-parse", "HEAD").decode().strip(), c)
        immutable(path, d); changed_decision = path.name
    results = [verify(json.loads(p.read_text())) for p in sorted((lane / "outcomes").glob("*.json"))]
    if any(r.get("contract_sha256") != CONTRACT_SHA256 for r in results):
        raise ValueError("OUTCOME_CONTRACT_CHANGED")
    status = {"schema": "qrds.xagent_spot_status.v1", "experiment_id": c["experiment_id"],
              "contract_sha256": CONTRACT_SHA256, "as_of_utc": now.isoformat(),
              "status": "AWAITING_FIRST_DECISION_WINDOW" if not list((lane / "decisions").glob("*.json")) else "PROSPECTIVE_EXPERIMENT_ACTIVE",
              "paired_outcome_count": len(results), "checkpoint": c["minimum_paired_outcomes"],
              "primary_excess_net_sum_diagnostic_not_nav": sum(r["primary_excess_net"] for r in results),
              "pending_price_or_seal": blocked, "new_decision": changed_decision,
              "scientific_credit": 0, "survivor_credit": 0, "parent_handoff_unchanged": True,
              "canonical_580_untouched": True, "h1_h31_untouched": True, "safety": c["safety"]}
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--acknowledge-publication-sha")
    args = parser.parse_args()
    print(json.dumps(run(args.repository.resolve(), datetime.now(timezone.utc), args.acknowledge_publication_sha), sort_keys=True))
