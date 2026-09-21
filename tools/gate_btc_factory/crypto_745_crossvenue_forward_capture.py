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

CHANNEL_ID = "CRYPTO_CROSS_VENUE_PRICE_DISCOVERY"
CHECKPOINT = 1440
PREBUFFER_SECONDS = 6.0
POSTBUFFER_SECONDS = 10.0
DEFAULT_POLL_SECONDS = 0.5
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


def parse_iso_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def normalize_okx_trades(obj: object) -> list[dict]:
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    out = []
    for row in rows:
        try:
            if row.get("instId") != "BTC-USDT-SWAP":
                continue
            ts = int(row["ts"])
            px = float(row["px"])
            if ts <= 0 or px <= 0:
                continue
            out.append({"ts_ms": ts, "price": row["px"], "trade_id": row.get("tradeId")})
        except Exception:
            continue
    return sorted(out, key=lambda x: x["ts_ms"])


def normalize_coinbase_trades(obj: object) -> list[dict]:
    rows = obj if isinstance(obj, list) else []
    out = []
    for row in rows:
        try:
            ts = parse_iso_ms(str(row["time"]))
            px = float(row["price"])
            if ts <= 0 or px <= 0:
                continue
            out.append({"ts_ms": ts, "price": row["price"], "trade_id": row.get("trade_id")})
        except Exception:
            continue
    return sorted(out, key=lambda x: x["ts_ms"])


def select_last_at_or_before(events: list[dict], cutoff_ms: int, max_age_ms: int = 5000) -> dict | None:
    candidates = [x for x in events if x["ts_ms"] <= cutoff_ms]
    if not candidates:
        return None
    event = max(candidates, key=lambda x: x["ts_ms"])
    if cutoff_ms - event["ts_ms"] > max_age_ms:
        return None
    return event


def select_first_at_or_after(events: list[dict], cutoff_ms: int, max_delay_ms: int = 5000) -> dict | None:
    candidates = [x for x in events if x["ts_ms"] >= cutoff_ms]
    if not candidates:
        return None
    event = min(candidates, key=lambda x: x["ts_ms"])
    if event["ts_ms"] - cutoff_ms > max_delay_ms:
        return None
    return event


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


def event_key(event: dict) -> tuple:
    trade_id = event.get("trade_id")
    if trade_id not in (None, ""):
        return ("id", str(trade_id))
    return ("fallback", int(event["ts_ms"]), str(event["price"]))


def merge_seen(store: dict[tuple, dict], events: list[dict], receipt_ms: int) -> None:
    for event in events:
        key = event_key(event)
        if key not in store:
            row = dict(event)
            row["first_seen_receipt_ms"] = receipt_ms
            store[key] = row


def poll_public_trades() -> tuple[tuple[bytes, object], tuple[bytes, object]]:
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_okx = ex.submit(
            get_json,
            "https://www.okx.com/api/v5/market/trades",
            {"instId": "BTC-USDT-SWAP", "limit": "500"},
        )
        f_cb = ex.submit(
            get_json,
            "https://api.exchange.coinbase.com/products/BTC-USD/trades",
            {"limit": "1000"},
        )
        return f_okx.result(), f_cb.result()


def collect_live_boundary_packet(
    boundary_ms: int,
    poll_seconds: float = DEFAULT_POLL_SECONDS,
    now_fn=time.time,
    sleep_fn=time.sleep,
    poll_fn=poll_public_trades,
) -> dict:
    """Collect only from a prospectively opened live window around one boundary.

    No history endpoint exists in this path. The window opens six seconds before
    the minute close, which is earlier than the frozen five-second freshness
    bound. A close absent from this physically observed buffer stays ineligible.
    """
    decision_ms = boundary_ms + 5000
    window_start_ms = boundary_ms - int(PREBUFFER_SECONDS * 1000)
    window_end_ms = boundary_ms + int(POSTBUFFER_SECONDS * 1000)
    now_ms = int(now_fn() * 1000)
    if now_ms > window_start_ms:
        raise RuntimeError("LIVE_PREBUFFER_MISSED_FAIL_CLOSED")
    delay = window_start_ms / 1000 - now_fn()
    if delay > 0:
        sleep_fn(delay)

    okx_seen: dict[tuple, dict] = {}
    cb_seen: dict[tuple, dict] = {}
    receipts = []
    raw_hashes = []
    while True:
        receipt_before_ms = int(now_fn() * 1000)
        try:
            (okx_raw, okx_obj), (cb_raw, cb_obj) = poll_fn()
            receipt_ms = int(now_fn() * 1000)
            merge_seen(okx_seen, normalize_okx_trades(okx_obj), receipt_ms)
            merge_seen(cb_seen, normalize_coinbase_trades(cb_obj), receipt_ms)
            receipts.append({"started_ms": receipt_before_ms, "completed_ms": receipt_ms, "ok": True})
            raw_hashes.append({
                "receipt_ms": receipt_ms,
                "okx_sha256": digest_bytes(okx_raw),
                "coinbase_sha256": digest_bytes(cb_raw),
            })
        except Exception as exc:
            receipts.append({
                "started_ms": receipt_before_ms,
                "completed_ms": int(now_fn() * 1000),
                "ok": False,
                "error": f"{type(exc).__name__}:{exc}",
            })
        if int(now_fn() * 1000) >= window_end_ms:
            break
        sleep_fn(max(0.01, poll_seconds))

    okx_events = sorted(okx_seen.values(), key=lambda x: x["ts_ms"])
    cb_events = sorted(cb_seen.values(), key=lambda x: x["ts_ms"])
    return {
        "boundary_ms": boundary_ms,
        "decision_ms": decision_ms,
        "capture_mode": "LIVE_PREBOUNDARY_BUFFER_ONLY",
        "history_endpoint_used": False,
        "window_start_ms": window_start_ms,
        "window_end_ms": window_end_ms,
        "captured_at_utc": utc_now(),
        "poll_receipts": receipts,
        "raw_poll_hashes": raw_hashes,
        "okx_events": okx_events,
        "coinbase_events": cb_events,
        "source_close": select_last_at_or_before(cb_events, boundary_ms),
        "execution_close": select_last_at_or_before(okx_events, boundary_ms),
        "entry": select_first_at_or_after(okx_events, decision_ms),
    }


def choose_first_future_boundary(now_s: float) -> int:
    candidate = (int(now_s) // 60 + 1) * 60
    # We must be alive before boundary-6s. If orchestration starts too late,
    # skip that minute rather than reconstructing it.
    if now_s > candidate - PREBUFFER_SECONDS - 1.0:
        candidate += 60
    return candidate


def finalize_pending(pending: dict, packet: dict) -> dict:
    reasons = list(pending.get("ineligible_reasons", []))
    exit_event = None
    target = pending.get("exit_target_ms")
    if target is None:
        reasons.append("ENTRY_MISSING")
    else:
        exit_event = select_first_at_or_after(packet["okx_events"], int(target))
        if exit_event is None:
            reasons.append("EXIT_MISSING_OR_DELAY_GT_5S")
    out = dict(pending)
    out["exit"] = exit_event
    out["ineligible_reasons"] = sorted(set(reasons))
    out["eligible_for_future_evaluation"] = not out["ineligible_reasons"]
    return out


def pending_from(prev_packet: dict | None, packet: dict) -> dict | None:
    if prev_packet is None:
        return None
    if packet["boundary_ms"] - prev_packet["boundary_ms"] != 60000:
        return None
    reasons = []
    for label, event in (
        ("SOURCE_PREV_CLOSE_MISSING", prev_packet.get("source_close")),
        ("SOURCE_CLOSE_MISSING", packet.get("source_close")),
        ("EXEC_PREV_CLOSE_MISSING", prev_packet.get("execution_close")),
        ("EXEC_CLOSE_MISSING", packet.get("execution_close")),
        ("ENTRY_MISSING_OR_DELAY_GT_5S", packet.get("entry")),
    ):
        if event is None:
            reasons.append(label)
    entry = packet.get("entry")
    return {
        "observation_id": str(packet["boundary_ms"]),
        "minute_close_ms": packet["boundary_ms"],
        "decision_ms": packet["decision_ms"],
        "source_previous_close": prev_packet.get("source_close"),
        "source_close": packet.get("source_close"),
        "execution_previous_close": prev_packet.get("execution_close"),
        "execution_close": packet.get("execution_close"),
        "entry": entry,
        "exit_target_ms": int(entry["ts_ms"]) + 60000 if entry else None,
        "ineligible_reasons": reasons,
    }


def capture_partition(admission_path: Path, boundaries: int = 4, poll_seconds: float = DEFAULT_POLL_SECONDS) -> dict:
    if boundaries < 3:
        raise ValueError("boundaries must be >= 3")
    _, evidence = qualified_source_cost(admission_path)
    started = utc_now()
    first_boundary_s = choose_first_future_boundary(time.time())
    packets: list[dict] = []
    observations: list[dict] = []
    previous = None
    pending = None
    for i in range(boundaries):
        boundary_s = first_boundary_s + i * 60
        packet = collect_live_boundary_packet(boundary_s * 1000, poll_seconds=poll_seconds)
        packets.append(packet)
        if pending is not None:
            observations.append(finalize_pending(pending, packet))
        pending = pending_from(previous, packet)
        previous = packet
    eligible = sum(x["eligible_for_future_evaluation"] for x in observations)
    out = {
        "schema": "qrds.factory.crypto_745_crossvenue_forward_partition.v2",
        "issue": 745,
        "channel_id": CHANNEL_ID,
        "collection_started_at_utc": started,
        "collection_finished_at_utc": utc_now(),
        "collection_contract": "LIVE_PREBOUNDARY_BUFFER_ONLY_NO_HISTORY_REPAIR",
        "source_cost_evidence_sha256": evidence,
        "forward_only": True,
        "history_endpoint_used": False,
        "historical_backfill_credit": 0,
        "scientific_credit": 0,
        "economics_read": False,
        "outcome_metrics_computed": False,
        "boundary_packet_count": len(packets),
        "observation_count": len(observations),
        "eligible_observation_count": eligible,
        "ineligible_observation_count": len(observations) - eligible,
        "unresolved_tail_zero_credit": pending is not None,
        "boundary_packets": packets,
        "observations": observations,
        "safety": SAFETY,
    }
    payload = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    out["partition_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def build_manifest(partition_dir: Path) -> dict:
    partition_files = sorted(partition_dir.glob("*.json"))
    seen: dict[str, dict] = {}
    duplicate_ids: list[str] = []
    partitions = []
    evidence_hashes = set()
    for path in partition_files:
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        schema = obj.get("schema")
        if schema not in {
            "qrds.factory.crypto_745_crossvenue_forward_partition.v1",
            "qrds.factory.crypto_745_crossvenue_forward_partition.v2",
        }:
            raise RuntimeError(f"BAD_PARTITION_SCHEMA:{path.name}")
        if obj.get("channel_id") != CHANNEL_ID or obj.get("economics_read") is not False:
            raise RuntimeError(f"PARTITION_AUTHORITY_MISMATCH:{path.name}")
        if schema.endswith(".v2") and obj.get("history_endpoint_used") is not False:
            raise RuntimeError(f"HISTORY_REPAIR_PROHIBITED:{path.name}")
        evidence_hashes.add(obj.get("source_cost_evidence_sha256"))
        partitions.append({
            "file": path.name,
            "sha256": digest_bytes(raw),
            "eligible_count": obj.get("eligible_observation_count", 0),
            "schema": schema,
        })
        for obs in obj.get("observations", []):
            if not obs.get("eligible_for_future_evaluation"):
                continue
            oid = str(obs.get("observation_id"))
            if oid in seen:
                duplicate_ids.append(oid)
                continue
            seen[oid] = obs
    if len(evidence_hashes) > 1:
        raise RuntimeError("SOURCE_COST_EVIDENCE_DRIFT_FAIL_CLOSED")
    ids = sorted(seen, key=int)
    eligible = len(ids)
    return {
        "schema": "qrds.factory.crypto_745_crossvenue_forward_manifest.v1",
        "issue": 745,
        "channel_id": CHANNEL_ID,
        "generated_at_utc": utc_now(),
        "partition_count": len(partitions),
        "partitions": partitions,
        "source_cost_evidence_sha256": next(iter(evidence_hashes), None),
        "eligible_unique_observation_count": eligible,
        "duplicate_observation_ids_zero_credit": sorted(set(duplicate_ids), key=int),
        "first_observation_id": ids[0] if ids else None,
        "last_observation_id": ids[-1] if ids else None,
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
    mode.add_argument("--partition-out")
    mode.add_argument("--manifest-out")
    ap.add_argument("--admission")
    ap.add_argument("--boundaries", type=int, default=4)
    ap.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    ap.add_argument("--partition-dir")
    args = ap.parse_args()
    if args.partition_out:
        if not args.admission:
            raise SystemExit("--admission is required with --partition-out")
        out = capture_partition(Path(args.admission), args.boundaries, args.poll_seconds)
        write_json(Path(args.partition_out), out)
        print(json.dumps({
            "status": "FORWARD_PARTITION_SEALED",
            "observations": out["observation_count"],
            "eligible": out["eligible_observation_count"],
            "economics_read": False,
            "orders": 0,
            "real_capital": 0,
        }, sort_keys=True))
    else:
        if not args.partition_dir:
            raise SystemExit("--partition-dir is required with --manifest-out")
        out = build_manifest(Path(args.partition_dir))
        write_json(Path(args.manifest_out), out)
        print(json.dumps({
            "status": "FORWARD_MANIFEST_UPDATED",
            "eligible_unique": out["eligible_unique_observation_count"],
            "checkpoint_ready": out["checkpoint_ready_for_dataset_binding"],
            "economics_read": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
