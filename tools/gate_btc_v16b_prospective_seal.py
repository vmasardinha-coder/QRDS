#!/usr/bin/env python3
"""Fail-closed staged prospective sealing for GATE BTC V16B.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders, no capital, no engine feed.
Evidence stages: SIGNAL -> ENTRY -> RESULT -> external DELTA attachment.
This changes auditability only; the frozen economic methodology is unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

CANDIDATE_ID = "GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811"
FIRST_SIGNAL = date(2026, 8, 13)
FIRST_ENTRY = date(2026, 8, 14)
FIRST_COMPLETE_EXIT = date(2026, 8, 21)
COST_BPS = 15.0
WEIGHT_PER_ASSET_UNSCALED = 0.05
TOL = 1e-9
SAFETY = {
    "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
    "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False,
}

SIGNAL_REQUIRED = {
    "signal_date_utc", "entry_date_utc", "candidate_id", "model_hash", "code_commit",
    "input_data_hashes", "universe_snapshot_id", "universe_snapshot_available_at_utc",
    "panel_hash", "model_state_hash", "eligible_universe_count", "liquidity_qualified_count",
    "eligible_scores", "score_ranking_desc", "preliminary_longs_10", "source_coverage",
    "status", "blocker_reason",
}
ENTRY_REQUIRED = {
    "signal_date_utc", "entry_date_utc", "candidate_id", "signal_seal_sha256",
    "shortability_evidence_hash", "shortability_checked_ranked", "long_executability",
    "longs_10", "shorts_10", "entry_instruments", "exposure", "trailing_vol",
    "turnover_estimate", "transaction_cost_bps", "source_coverage", "status", "blocker_reason",
}
RESULT_REQUIRED = {
    "signal_date_utc", "entry_date_utc", "exit_date_utc", "candidate_id", "entry_seal_sha256",
    "execution_ledger_hash", "price_source_hashes", "per_asset_pnl", "transaction_cost",
    "short_funding", "funding_evidence_hash", "gross_long_pnl", "gross_short_pnl", "net_pnl",
    "btc_benchmark_return", "btc_entry_price", "btc_exit_price", "btc_source_hash",
    "source_coverage", "status", "blocker_reason",
}


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def parse_date(v: str) -> date:
    return date.fromisoformat(v)


def parse_utc(v: str) -> datetime:
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include UTC offset/Z")
    return dt.astimezone(timezone.utc)


def close_after_day(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _event_time(now: datetime | None) -> datetime:
    x = now or datetime.now(timezone.utc)
    if x.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return x.astimezone(timezone.utc)


def _stamp(row: dict[str, Any], event_type: str, created: datetime) -> dict[str, Any]:
    event = dict(row)
    event.update(SAFETY)
    event["event_type"] = event_type
    event["event_created_at_utc"] = created.isoformat().replace("+00:00", "Z")
    event["seal_sha256"] = sha256_obj({k: event[k] for k in sorted(event) if k != "seal_sha256"})
    return event


def _require_fields(row: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - row.keys())
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    if "external_delta_print" in row or "external_delta" in row:
        raise ValueError("external Delta is forbidden before the result seal")
    if row["candidate_id"] != CANDIDATE_ID:
        raise ValueError("unexpected candidate_id")


def _status(row: dict[str, Any]) -> str:
    status = row["status"]
    if status not in {"OK", "BLOCKED"}:
        raise ValueError("status must be OK or BLOCKED")
    if status == "OK" and row["blocker_reason"] not in (None, ""):
        raise ValueError("OK row cannot have blocker_reason")
    if status == "BLOCKED" and not row["blocker_reason"]:
        raise ValueError("BLOCKED row requires blocker_reason")
    return status


def _require_hash(v: Any, name: str, length: int = 64) -> None:
    if not isinstance(v, str) or len(v) != length or any(c not in "0123456789abcdefABCDEF" for c in v):
        raise ValueError(f"{name} must be a {length}-hex string")


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"invalid JSONL at line {n}: {e}") from e
    return out


def _unique_stage(events: list[dict[str, Any]], event_type: str, signal_date: str) -> dict[str, Any]:
    rows = [e for e in events if e.get("event_type") == event_type and e.get("signal_date_utc") == signal_date]
    if len(rows) != 1:
        raise ValueError(f"requires exactly one {event_type} for signal {signal_date}")
    return rows[0]


def validate_signal_row(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, SIGNAL_REQUIRED)
    signal, entry = parse_date(row["signal_date_utc"]), parse_date(row["entry_date_utc"])
    if signal < FIRST_SIGNAL or entry < FIRST_ENTRY:
        raise ValueError("pre-freeze/backfilled signal cannot count as prospective")
    if not signal < entry:
        raise ValueError("signal_date_utc must precede entry_date_utc")
    created = _event_time(now)
    if not (close_after_day(signal) <= created < close_after_day(entry)):
        raise ValueError("signal seal must be created after signal-day UTC close and before entry-day UTC close")
    _require_hash(row["model_hash"], "model_hash")
    _require_hash(row["code_commit"], "code_commit", 40)
    _require_hash(row["panel_hash"], "panel_hash")
    _require_hash(row["model_state_hash"], "model_state_hash")
    if not isinstance(row["input_data_hashes"], dict) or not row["input_data_hashes"]:
        raise ValueError("input_data_hashes must be a non-empty mapping")
    for k, v in row["input_data_hashes"].items():
        _require_hash(v, f"input_data_hashes[{k}]")
    available = parse_utc(row["universe_snapshot_available_at_utc"])
    if available > close_after_day(signal):
        raise ValueError("universe snapshot must be demonstrably available by signal-day UTC close")
    for k in ("eligible_universe_count", "liquidity_qualified_count"):
        if not isinstance(row[k], int) or row[k] < 0:
            raise ValueError(f"{k} must be a non-negative integer")
    if row["liquidity_qualified_count"] > row["eligible_universe_count"]:
        raise ValueError("liquidity-qualified count exceeds eligible universe")
    status = _status(row)
    if status == "OK":
        scores, ranking, longs = row["eligible_scores"], row["score_ranking_desc"], row["preliminary_longs_10"]
        if not isinstance(scores, dict) or len(scores) != row["liquidity_qualified_count"]:
            raise ValueError("eligible_scores must cover every liquidity-qualified asset")
        if not isinstance(ranking, list) or len(ranking) != len(scores) or len(set(ranking)) != len(ranking):
            raise ValueError("score_ranking_desc must be a unique full ranking")
        if set(ranking) != set(scores):
            raise ValueError("score_ranking_desc and eligible_scores must cover the same assets")
        expected = sorted(scores, key=lambda a: (-float(scores[a]), a))
        if ranking != expected:
            raise ValueError("score_ranking_desc is inconsistent with eligible_scores")
        if len(longs) != 10 or longs != ranking[:10]:
            raise ValueError("preliminary_longs_10 must equal the top 10 frozen score ranking")
    else:
        if row["eligible_scores"] not in ({}, None) or row["score_ranking_desc"] not in ([], None) or row["preliminary_longs_10"] not in ([], None):
            raise ValueError("BLOCKED signal cannot carry a synthetic ranking")
    return _stamp(row, "V16B_SIGNAL_SEAL", created)


def seal_signal(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    event = validate_signal_row(row, now=now)
    events = load_events(ledger)
    if any(e.get("event_type") == "V16B_SIGNAL_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("signal already sealed; append-only ledger forbids replacement")
    append_jsonl(ledger, event)
    return event


def validate_entry_row(row: dict[str, Any], signal_event: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, ENTRY_REQUIRED)
    if signal_event["signal_date_utc"] != row["signal_date_utc"] or signal_event["entry_date_utc"] != row["entry_date_utc"]:
        raise ValueError("entry dates do not match signal seal")
    if row["signal_seal_sha256"] != signal_event["seal_sha256"]:
        raise ValueError("signal_seal_sha256 does not match sealed signal")
    entry = parse_date(row["entry_date_utc"])
    created = _event_time(now)
    if created < parse_utc(signal_event["event_created_at_utc"]) or created >= close_after_day(entry):
        raise ValueError("entry seal must follow signal seal and be created before entry-day UTC close")
    _require_hash(row["shortability_evidence_hash"], "shortability_evidence_hash")
    status = _status(row)
    if status == "OK":
        if signal_event["status"] != "OK":
            raise ValueError("cannot create OK entry from BLOCKED signal")
        longs, shorts = row["longs_10"], row["shorts_10"]
        if not isinstance(longs, list) or len(longs) != 10 or len(set(longs)) != 10:
            raise ValueError("OK entry requires exactly 10 unique longs")
        if not isinstance(shorts, list) or len(shorts) != 10 or len(set(shorts)) != 10:
            raise ValueError("OK entry requires exactly 10 unique shorts")
        if set(longs) & set(shorts):
            raise ValueError("same asset cannot be both long and short")
        if longs != signal_event["preliminary_longs_10"]:
            raise ValueError("longs_10 cannot change after the frozen signal ranking")
        long_exec = row["long_executability"]
        if not isinstance(long_exec, dict) or set(long_exec) != set(longs):
            raise ValueError("long_executability must cover exactly the selected longs")
        if any(not isinstance(v, dict) or v.get("executable") is not True or not v.get("evidence_ref") for v in long_exec.values()):
            raise ValueError("all selected longs require positive predeclared executability evidence")
        checked = row["shortability_checked_ranked"]
        if not isinstance(checked, list) or not checked:
            raise ValueError("shortability_checked_ranked is required")
        bottom_up = list(reversed(signal_event["score_ranking_desc"]))
        if len(checked) > len(bottom_up):
            raise ValueError("shortability checks exceed frozen ranking")
        selected = []
        for i, item in enumerate(checked):
            if not isinstance(item, dict) or item.get("asset") != bottom_up[i] or "shortable" not in item or not item.get("evidence_ref"):
                raise ValueError("shortability checks must follow the frozen bottom-up ranking with evidence")
            if item["shortable"] is True:
                selected.append(item["asset"])
                if len(selected) == 10:
                    if i != len(checked) - 1:
                        raise ValueError("shortability checks must stop when the 10th short is found")
                    break
        if len(selected) != 10 or shorts != selected:
            raise ValueError("shorts_10 must be the first 10 causally shortable assets in frozen bottom-up rank order")
        instruments = row["entry_instruments"]
        selected_assets = set(longs) | set(shorts)
        if not isinstance(instruments, dict) or set(instruments) != selected_assets or any(not isinstance(v, str) or not v for v in instruments.values()):
            raise ValueError("entry_instruments must map exactly the 20 selected assets")
        exposure = float(row["exposure"])
        if not (0.0 < exposure <= 1.0):
            raise ValueError("exposure must be in (0,1]")
        if float(row["trailing_vol"]) <= 0 or float(row["turnover_estimate"]) < 0:
            raise ValueError("invalid trailing_vol/turnover_estimate")
        if abs(float(row["transaction_cost_bps"]) - COST_BPS) > TOL:
            raise ValueError("transaction_cost_bps must equal the frozen 15 bps")
    else:
        for k in ("exposure", "trailing_vol", "turnover_estimate", "transaction_cost_bps"):
            if row[k] is not None:
                raise ValueError(f"BLOCKED entry must not carry synthetic field {k}")
        if row["longs_10"] not in ([], None) or row["shorts_10"] not in ([], None) or row["entry_instruments"] not in ({}, None):
            raise ValueError("BLOCKED entry cannot carry synthetic holdings")
    return _stamp(row, "V16B_ENTRY_SEAL", created)


def seal_entry(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    events = load_events(ledger)
    signal_event = _unique_stage(events, "V16B_SIGNAL_SEAL", row.get("signal_date_utc", ""))
    event = validate_entry_row(row, signal_event, now=now)
    if any(e.get("event_type") == "V16B_ENTRY_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("entry already sealed; append-only ledger forbids replacement")
    append_jsonl(ledger, event)
    return event


def validate_result_row(row: dict[str, Any], entry_event: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    _require_fields(row, RESULT_REQUIRED)
    signal, entry, exit_ = parse_date(row["signal_date_utc"]), parse_date(row["entry_date_utc"]), parse_date(row["exit_date_utc"])
    if signal < FIRST_SIGNAL or entry < FIRST_ENTRY or exit_ < FIRST_COMPLETE_EXIT:
        raise ValueError("pre-freeze/incomplete result cannot count as prospective")
    if not signal < entry < exit_:
        raise ValueError("dates must satisfy signal < entry < exit")
    if entry_event["signal_date_utc"] != row["signal_date_utc"] or entry_event["entry_date_utc"] != row["entry_date_utc"]:
        raise ValueError("result dates do not match entry seal")
    if row["entry_seal_sha256"] != entry_event["seal_sha256"]:
        raise ValueError("entry_seal_sha256 does not match sealed entry")
    created = _event_time(now)
    if created < close_after_day(exit_):
        raise ValueError("result seal cannot be created before exit-day UTC close")
    status = _status(row)
    if status == "OK":
        if entry_event["status"] != "OK":
            raise ValueError("cannot create OK result from BLOCKED entry")
        for hname in ("execution_ledger_hash", "funding_evidence_hash", "btc_source_hash"):
            _require_hash(row[hname], hname)
        if not isinstance(row["price_source_hashes"], dict) or not row["price_source_hashes"]:
            raise ValueError("price_source_hashes must be a non-empty mapping")
        for k, v in row["price_source_hashes"].items():
            _require_hash(v, f"price_source_hashes[{k}]")
        details = row["per_asset_pnl"]
        expected_assets = set(entry_event["longs_10"]) | set(entry_event["shorts_10"])
        if not isinstance(details, list) or len(details) != 20:
            raise ValueError("per_asset_pnl must contain exactly 20 selected assets")
        seen, long_sum, short_sum = set(), 0.0, 0.0
        exposure = float(entry_event["exposure"])
        for item in details:
            required = {"asset", "side", "instrument", "entry_price", "exit_price", "raw_return", "weight", "weighted_pnl", "price_source_hash"}
            if not isinstance(item, dict) or required - item.keys():
                raise ValueError("per_asset_pnl item missing fields")
            asset = item["asset"]
            if asset in seen or asset not in expected_assets:
                raise ValueError("per_asset_pnl assets must uniquely match entry holdings")
            seen.add(asset)
            side = "LONG" if asset in entry_event["longs_10"] else "SHORT"
            if item["side"] != side or item["instrument"] != entry_event["entry_instruments"][asset]:
                raise ValueError("per_asset_pnl side/instrument mismatch")
            ep, xp = float(item["entry_price"]), float(item["exit_price"])
            if ep <= 0 or xp <= 0:
                raise ValueError("entry/exit prices must be positive")
            raw = xp / ep - 1.0
            if abs(float(item["raw_return"]) - raw) > 1e-8:
                raise ValueError("raw_return inconsistent with entry/exit prices")
            weight = WEIGHT_PER_ASSET_UNSCALED * exposure * (1.0 if side == "LONG" else -1.0)
            if abs(float(item["weight"]) - weight) > 1e-10:
                raise ValueError("per-asset weight inconsistent with frozen portfolio")
            wpnl = weight * raw
            if abs(float(item["weighted_pnl"]) - wpnl) > 1e-8:
                raise ValueError("weighted_pnl inconsistent with frozen weight and raw return")
            _require_hash(item["price_source_hash"], "per_asset price_source_hash")
            if side == "LONG":
                long_sum += wpnl
            else:
                short_sum += wpnl
        if seen != expected_assets:
            raise ValueError("per_asset_pnl does not cover exact entry holdings")
        if abs(float(row["gross_long_pnl"]) - long_sum) > 1e-8 or abs(float(row["gross_short_pnl"]) - short_sum) > 1e-8:
            raise ValueError("gross leg PnL inconsistent with per-asset details")
        funding = row["short_funding"]
        if not isinstance(funding, dict) or set(funding) != set(entry_event["shorts_10"]):
            raise ValueError("short_funding must cover exactly the 10 selected shorts")
        funding_total = sum(float(v) for v in funding.values())
        expected_cost = COST_BPS / 10000.0 * float(entry_event["turnover_estimate"])
        if abs(float(row["transaction_cost"]) - expected_cost) > 1e-10:
            raise ValueError("transaction_cost inconsistent with frozen cost and sealed turnover")
        expected_net = long_sum + short_sum + funding_total - expected_cost
        if abs(float(row["net_pnl"]) - expected_net) > 1e-8:
            raise ValueError("net_pnl inconsistent with sealed legs, funding and cost")
        bp0, bp1 = float(row["btc_entry_price"]), float(row["btc_exit_price"])
        if bp0 <= 0 or bp1 <= 0 or abs(float(row["btc_benchmark_return"]) - (bp1 / bp0 - 1.0)) > 1e-8:
            raise ValueError("btc_benchmark_return inconsistent with sealed BTC prices")
    else:
        for k in ("transaction_cost", "short_funding", "gross_long_pnl", "gross_short_pnl", "net_pnl", "btc_benchmark_return", "btc_entry_price", "btc_exit_price"):
            if row[k] is not None:
                raise ValueError(f"BLOCKED result must not contain synthetic economic field {k}")
        if row["per_asset_pnl"] not in ([], None):
            raise ValueError("BLOCKED result cannot carry synthetic per-asset PnL")
    return _stamp(row, "V16B_RESULT_SEAL", created)


def seal_result(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    events = load_events(ledger)
    entry_event = _unique_stage(events, "V16B_ENTRY_SEAL", row.get("signal_date_utc", ""))
    event = validate_result_row(row, entry_event, now=now)
    if any(e.get("event_type") == "V16B_RESULT_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("result already sealed; append-only ledger forbids replacement")
    append_jsonl(ledger, event)
    return event


def validate_self_row(row: dict[str, Any]) -> dict[str, Any]:
    raise ValueError("legacy one-stage V16B self-result sealing is disabled; use signal -> entry -> result staged seals")


def seal_self(input_path: Path, ledger: Path) -> dict[str, Any]:
    raise ValueError("legacy one-stage V16B self-result sealing is disabled; use signal -> entry -> result staged seals")


def attach_delta(signal_date: str, delta_print: float, source_timestamp: str, source_ref: str, ledger: Path) -> dict[str, Any]:
    parse_date(signal_date)
    events = load_events(ledger)
    result = _unique_stage(events, "V16B_RESULT_SEAL", signal_date)
    if any(e.get("event_type") == "EXTERNAL_DELTA_ATTACHMENT" and e.get("signal_date_utc") == signal_date for e in events):
        raise ValueError("external Delta already attached for this signal; append-only ledger forbids replacement")
    event = {
        "event_type": "EXTERNAL_DELTA_ATTACHMENT", "signal_date_utc": signal_date,
        "candidate_id": CANDIDATE_ID, "result_seal_sha256": result["seal_sha256"],
        "external_delta_print": float(delta_print), "external_source_timestamp": source_timestamp,
        "external_source_ref": source_ref, **SAFETY,
    }
    event["seal_sha256"] = sha256_obj({k: event[k] for k in sorted(event) if k != "seal_sha256"})
    append_jsonl(ledger, event)
    return event


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("seal-signal", "seal-entry", "seal-result"):
        a = sub.add_parser(name)
        a.add_argument("--input", required=True)
        a.add_argument("--ledger", required=True)
    b = sub.add_parser("attach-delta")
    b.add_argument("--signal-date", required=True)
    b.add_argument("--delta-print", required=True, type=float)
    b.add_argument("--source-timestamp", required=True)
    b.add_argument("--source-ref", required=True)
    b.add_argument("--ledger", required=True)
    args = p.parse_args()
    if args.cmd == "seal-signal":
        event = seal_signal(Path(args.input), Path(args.ledger))
    elif args.cmd == "seal-entry":
        event = seal_entry(Path(args.input), Path(args.ledger))
    elif args.cmd == "seal-result":
        event = seal_result(Path(args.input), Path(args.ledger))
    else:
        event = attach_delta(args.signal_date, args.delta_print, args.source_timestamp, args.source_ref, Path(args.ledger))
    print(json.dumps({"status": "PASS", "event_type": event["event_type"], "seal_sha256": event["seal_sha256"], "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
