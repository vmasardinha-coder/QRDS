#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

CHANNEL_ID = "CRYPTO_SPOT_PERP_BASIS_FUNDING"
CHECKPOINT = 60
UA = {"User-Agent": "QRDS-research-only/1.0"}
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_LATE_SEAL": True,
    "NO_COUNTER_RESET": True,
    "NO_RETUNE": True,
    "FAIL_CLOSED": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def get_json(url: str, params: dict[str, str] | None = None) -> tuple[bytes, object]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return raw, json.loads(raw.decode("utf-8"))


def qualified_source_cost(path: Path) -> tuple[dict, str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = {x.get("channel_id"): x for x in obj.get("channels", [])}
    row = rows.get(CHANNEL_ID)
    if not row or row.get("adjudication_decision") != "SOURCE_COST_QUALIFIED":
        raise RuntimeError("SOURCE_COST_NOT_QUALIFIED_FAIL_CLOSED")
    if obj.get("outcomes_read") is not False or obj.get("economics_read") is not False:
        raise RuntimeError("SOURCE_COST_AUTHORITY_MISMATCH_FAIL_CLOSED")
    evidence = str(obj.get("evidence_sha256") or "")
    if not evidence:
        raise RuntimeError("SOURCE_COST_EVIDENCE_HASH_MISSING_FAIL_CLOSED")
    return obj, evidence


def normalize_ticker(inst: str, obj: object) -> dict | None:
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    row = rows[0] if rows else {}
    try:
        if obj.get("code") != "0" or row.get("instId") != inst:
            return None
        bid = float(row.get("bidPx") or 0)
        ask = float(row.get("askPx") or 0)
        ts = int(row.get("ts") or 0)
        if bid <= 0 or ask <= 0 or ts <= 0 or ask < bid:
            return None
        return {"instId": inst, "bid": row["bidPx"], "ask": row["askPx"], "ts_ms": ts}
    except Exception:
        return None


def normalize_funding(obj: object) -> dict | None:
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    row = rows[0] if rows else {}
    try:
        if obj.get("code") != "0" or row.get("instId") != "BTC-USDT-SWAP":
            return None
        funding_time = int(row.get("fundingTime") or 0)
        ts = int(row.get("ts") or 0)
        rate = row.get("fundingRate")
        if funding_time <= 0 or ts <= 0 or rate in (None, ""):
            return None
        float(rate)
        return {
            "instId": "BTC-USDT-SWAP",
            "funding_rate": rate,
            "funding_time_ms": funding_time,
            "next_funding_time_ms": int(row.get("nextFundingTime") or 0),
            "ts_ms": ts,
            "sett_state": row.get("settState"),
            "sett_funding_rate": row.get("settFundingRate"),
        }
    except Exception:
        return None


def fetch_funding() -> tuple[bytes, dict | None]:
    raw, obj = get_json("https://www.okx.com/api/v5/public/funding-rate", {"instId": "BTC-USDT-SWAP"})
    return raw, normalize_funding(obj)


def fetch_quote_pair() -> dict:
    def one(inst: str):
        raw, obj = get_json("https://www.okx.com/api/v5/market/ticker", {"instId": inst})
        return raw, normalize_ticker(inst, obj)
    with ThreadPoolExecutor(max_workers=2) as ex:
        a = ex.submit(one, "BTC-USDT")
        b = ex.submit(one, "BTC-USDT-SWAP")
        spot_raw, spot = a.result()
        perp_raw, perp = b.result()
    return {
        "captured_at_ms": int(time.time() * 1000),
        "spot": spot,
        "perp": perp,
        "spot_raw_sha256": digest_bytes(spot_raw),
        "perp_raw_sha256": digest_bytes(perp_raw),
    }


def synchronized_pair(sample: dict, relation: str, clock_ms: int) -> bool:
    spot = sample.get("spot")
    perp = sample.get("perp")
    if not spot or not perp:
        return False
    if abs(int(spot["ts_ms"]) - int(perp["ts_ms"])) > 5000:
        return False
    if relation == "at_or_before":
        return int(spot["ts_ms"]) <= clock_ms and int(perp["ts_ms"]) <= clock_ms
    if relation == "at_or_after":
        return int(spot["ts_ms"]) >= clock_ms and int(perp["ts_ms"]) >= clock_ms
    raise ValueError(relation)


def select_latest_predecision(samples: list[dict], decision_ms: int) -> dict | None:
    good = [x for x in samples if synchronized_pair(x, "at_or_before", decision_ms)]
    if not good:
        return None
    return max(good, key=lambda x: max(int(x["spot"]["ts_ms"]), int(x["perp"]["ts_ms"])))


def select_first_postclock(samples: list[dict], clock_ms: int, max_delay_ms: int | None = None) -> dict | None:
    good = [x for x in samples if synchronized_pair(x, "at_or_after", clock_ms)]
    if max_delay_ms is not None:
        good = [
            x for x in good
            if max(int(x["spot"]["ts_ms"]), int(x["perp"]["ts_ms"])) - clock_ms <= max_delay_ms
        ]
    if not good:
        return None
    return min(good, key=lambda x: max(int(x["spot"]["ts_ms"]), int(x["perp"]["ts_ms"])))


def select_latest_funding_before(samples: list[dict], decision_ms: int, settlement_ms: int) -> dict | None:
    good = [
        x for x in samples
        if x and int(x.get("ts_ms", 0)) <= decision_ms and int(x.get("funding_time_ms", 0)) == settlement_ms
    ]
    if not good:
        return None
    return max(good, key=lambda x: int(x["ts_ms"]))


def sleep_until_ms(epoch_ms: int) -> None:
    delay = epoch_ms / 1000 - time.time()
    if delay > 0:
        time.sleep(delay)


def capture_attempt(admission_path: Path, max_wait_seconds: int = 420, poll_seconds: float = 0.5) -> dict:
    _, evidence = qualified_source_cost(admission_path)
    funding_raw, initial_funding = fetch_funding()
    now_ms = int(time.time() * 1000)
    base = {
        "schema": "qrds.factory.crypto_745_basis_forward_attempt.v1",
        "issue": 745,
        "channel_id": CHANNEL_ID,
        "generated_at_utc": utc_now(),
        "source_cost_evidence_sha256": evidence,
        "forward_only": True,
        "historical_backfill_credit": 0,
        "scientific_credit": 0,
        "economics_read": False,
        "outcome_metrics_computed": False,
        "safety": SAFETY,
        "initial_funding_raw_sha256": digest_bytes(funding_raw),
    }
    if initial_funding is None:
        return {**base, "status": "FUNDING_SOURCE_FAIL_CLOSED", "attempted_window": False, "eligible_observation_count": 0}
    settlement_ms = int(initial_funding["funding_time_ms"])
    decision_ms = settlement_ms - 300000
    base.update({"settlement_ms": settlement_ms, "decision_ms": decision_ms, "initial_funding": initial_funding})
    # Do not reinterpret nextFundingTime or reconstruct a missed decision. If fundingTime
    # is not a future settlement with enough predecision runway, this run gets zero credit.
    if settlement_ms <= now_ms:
        return {**base, "status": "NONFUTURE_FUNDING_TIME_FAIL_CLOSED", "attempted_window": False, "eligible_observation_count": 0}
    start_poll_ms = decision_ms - 3000
    wait_ms = start_poll_ms - now_ms
    if wait_ms > max_wait_seconds * 1000:
        return {**base, "status": "WAITING_FUTURE_DECISION_WINDOW", "attempted_window": False, "eligible_observation_count": 0}
    if wait_ms < -1000:
        return {**base, "status": "MISSED_PREDECISION_WINDOW_ZERO_CREDIT", "attempted_window": False, "eligible_observation_count": 0}

    sleep_until_ms(start_poll_ms)
    quote_samples: list[dict] = []
    funding_samples: list[dict] = []
    end_decision_poll = decision_ms + 5000
    while int(time.time() * 1000) <= end_decision_poll:
        with ThreadPoolExecutor(max_workers=2) as ex:
            qf = ex.submit(fetch_quote_pair)
            ff = ex.submit(fetch_funding)
            quote_samples.append(qf.result())
            fraw, frow = ff.result()
        if frow is not None:
            frow = dict(frow)
            frow["raw_sha256"] = digest_bytes(fraw)
            funding_samples.append(frow)
        time.sleep(poll_seconds)

    predecision = select_latest_predecision(quote_samples, decision_ms)
    entry = select_first_postclock(quote_samples, decision_ms, None)
    funding_bound = select_latest_funding_before(funding_samples, decision_ms, settlement_ms)
    reasons = []
    if predecision is None:
        reasons.append("PREDECISION_SYNCHRONIZED_PAIR_MISSING")
    if entry is None:
        reasons.append("ENTRY_SYNCHRONIZED_PAIR_MISSING")
    elif max(int(entry["spot"]["ts_ms"]), int(entry["perp"]["ts_ms"])) >= settlement_ms:
        reasons.append("ENTRY_NOT_BEFORE_SETTLEMENT")
    if funding_bound is None:
        reasons.append("FUNDING_RATE_NOT_BOUND_BEFORE_DECISION")

    # The exit itself is still captured even when an earlier leg is ineligible, so the
    # attempted settlement is auditable. No return or PnL is computed.
    sleep_until_ms(settlement_ms)
    exit_samples = []
    exit_deadline = settlement_ms + 60000
    while int(time.time() * 1000) <= exit_deadline:
        sample = fetch_quote_pair()
        exit_samples.append(sample)
        exit_pair = select_first_postclock(exit_samples, settlement_ms, 60000)
        if exit_pair is not None:
            break
        time.sleep(poll_seconds)
    else:
        exit_pair = None
    if exit_pair is None:
        reasons.append("EXIT_SYNCHRONIZED_PAIR_MISSING_OR_DELAY_GT_60S")

    eligible = not reasons
    observation = {
        "observation_id": str(settlement_ms),
        "decision_ms": decision_ms,
        "settlement_ms": settlement_ms,
        "predecision_pair": predecision,
        "entry_pair": entry,
        "funding_bound": funding_bound,
        "exit_pair": exit_pair,
        "ineligible_reasons": sorted(set(reasons)),
        "eligible_for_future_evaluation": eligible,
    }
    out = {
        **base,
        "status": "SEALED_ELIGIBLE_OBSERVATION" if eligible else "SEALED_INELIGIBLE_ZERO_CREDIT",
        "attempted_window": True,
        "eligible_observation_count": int(eligible),
        "ineligible_observation_count": int(not eligible),
        "quote_samples_decision_window": quote_samples,
        "funding_samples_decision_window": funding_samples,
        "quote_samples_exit_window": exit_samples,
        "observation": observation,
    }
    payload = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    out["attempt_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def build_manifest(partition_dir: Path) -> dict:
    seen = set()
    duplicate = []
    partitions = []
    evidence_hashes = set()
    eligible = 0
    ineligible = 0
    for path in sorted(partition_dir.glob("*.json")):
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        if obj.get("schema") != "qrds.factory.crypto_745_basis_forward_attempt.v1":
            raise RuntimeError(f"BAD_ATTEMPT_SCHEMA:{path.name}")
        if obj.get("channel_id") != CHANNEL_ID or obj.get("economics_read") is not False:
            raise RuntimeError(f"ATTEMPT_AUTHORITY_MISMATCH:{path.name}")
        if not obj.get("attempted_window"):
            continue
        evidence_hashes.add(obj.get("source_cost_evidence_sha256"))
        obs = obj.get("observation") or {}
        oid = str(obs.get("observation_id") or "")
        if not oid:
            raise RuntimeError(f"MISSING_OBSERVATION_ID:{path.name}")
        partitions.append({"file": path.name, "sha256": digest_bytes(raw), "observation_id": oid, "eligible": bool(obs.get("eligible_for_future_evaluation"))})
        if oid in seen:
            duplicate.append(oid)
            continue
        seen.add(oid)
        if obs.get("eligible_for_future_evaluation"):
            eligible += 1
        else:
            ineligible += 1
    if len(evidence_hashes) > 1:
        raise RuntimeError("SOURCE_COST_EVIDENCE_DRIFT_FAIL_CLOSED")
    ids = sorted(seen, key=int)
    return {
        "schema": "qrds.factory.crypto_745_basis_forward_manifest.v1",
        "issue": 745,
        "channel_id": CHANNEL_ID,
        "generated_at_utc": utc_now(),
        "attempted_unique_settlements": len(seen),
        "eligible_unique_observation_count": eligible,
        "ineligible_unique_observation_count": ineligible,
        "duplicate_observation_ids_zero_credit": sorted(set(duplicate), key=int),
        "first_observation_id": ids[0] if ids else None,
        "last_observation_id": ids[-1] if ids else None,
        "partition_count": len(partitions),
        "partitions": partitions,
        "source_cost_evidence_sha256": next(iter(evidence_hashes), None),
        "checkpoint_count": CHECKPOINT,
        "checkpoint_ready_for_dataset_binding": eligible >= CHECKPOINT,
        "economics_read": False,
        "economics_read_allowed": False,
        "next_action": "FREEZE_IMMUTABLE_DATASET_BINDING" if eligible >= CHECKPOINT else "CONTINUE_FORWARD_COLLECTION",
        "historical_backfill_credit": 0,
        "scientific_credit": 0,
        "safety": SAFETY,
    }


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--attempt-out")
    mode.add_argument("--manifest-out")
    ap.add_argument("--admission")
    ap.add_argument("--max-wait-seconds", type=int, default=420)
    ap.add_argument("--poll-seconds", type=float, default=0.5)
    ap.add_argument("--partition-dir")
    args = ap.parse_args()
    if args.attempt_out:
        if not args.admission:
            raise SystemExit("--admission is required with --attempt-out")
        out = capture_attempt(Path(args.admission), args.max_wait_seconds, args.poll_seconds)
        write_json(Path(args.attempt_out), out)
        print(json.dumps({"status":out["status"],"attempted_window":out["attempted_window"],"eligible":out["eligible_observation_count"],"economics_read":False,"orders":0,"real_capital":0}, sort_keys=True))
    else:
        if not args.partition_dir:
            raise SystemExit("--partition-dir is required with --manifest-out")
        out = build_manifest(Path(args.partition_dir))
        write_json(Path(args.manifest_out), out)
        print(json.dumps({"status":"BASIS_FORWARD_MANIFEST_UPDATED","eligible_unique":out["eligible_unique_observation_count"],"checkpoint_ready":out["checkpoint_ready_for_dataset_binding"],"economics_read":False}, sort_keys=True))


if __name__ == "__main__":
    main()
