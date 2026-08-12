#!/usr/bin/env python3
"""Canonical dual-rank staged evidence chain for prospective V16B.

Preserves the frozen engine's separate sort directions: descending score order
for longs and ascending score order for shorts. Ties are not re-resolved here;
the exact generated order is sealed. RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import gate_btc_v16b_prospective_seal as base

CANDIDATE_ID = base.CANDIDATE_ID
SAFETY = base.SAFETY
COST_BPS = base.COST_BPS
TOL = base.TOL

SIGNAL_REQUIRED = {
    "signal_date_utc", "entry_date_utc", "candidate_id", "model_hash", "code_commit",
    "input_data_hashes", "universe_snapshot_id", "universe_snapshot_available_at_utc",
    "panel_hash", "model_state_hash", "eligible_universe_count", "liquidity_qualified_count",
    "eligible_scores", "long_ranking_desc", "short_ranking_asc", "preliminary_longs_10",
    "risk_state", "source_coverage", "status", "blocker_reason",
}
ENTRY_REQUIRED = base.ENTRY_REQUIRED


def _monotone(ranking: list[str], scores: dict[str, Any], descending: bool) -> bool:
    vals = [float(scores[a]) for a in ranking]
    if descending:
        return all(vals[i] + TOL >= vals[i + 1] for i in range(len(vals) - 1))
    return all(vals[i] <= vals[i + 1] + TOL for i in range(len(vals) - 1))


def validate_signal_row(row: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    base._require_fields(row, SIGNAL_REQUIRED)
    signal, entry = base.parse_date(row["signal_date_utc"]), base.parse_date(row["entry_date_utc"])
    if signal < base.FIRST_SIGNAL or entry < base.FIRST_ENTRY:
        raise ValueError("pre-freeze/backfilled signal cannot count as prospective")
    if not signal < entry:
        raise ValueError("signal_date_utc must precede entry_date_utc")
    created = base._event_time(now)
    if not (base.close_after_day(signal) <= created < base.close_after_day(entry)):
        raise ValueError("signal seal must be created after signal-day UTC close and before entry-day UTC close")
    base._require_hash(row["model_hash"], "model_hash")
    base._require_hash(row["code_commit"], "code_commit", 40)
    base._require_hash(row["panel_hash"], "panel_hash")
    base._require_hash(row["model_state_hash"], "model_state_hash")
    if not isinstance(row["input_data_hashes"], dict) or not row["input_data_hashes"]:
        raise ValueError("input_data_hashes must be non-empty")
    for k, v in row["input_data_hashes"].items():
        base._require_hash(v, f"input_data_hashes[{k}]")
    if base.parse_utc(row["universe_snapshot_available_at_utc"]) > base.close_after_day(signal):
        raise ValueError("universe snapshot must be demonstrably available by signal-day UTC close")
    for k in ("eligible_universe_count", "liquidity_qualified_count"):
        if not isinstance(row[k], int) or row[k] < 0:
            raise ValueError(f"{k} must be a non-negative integer")
    if row["liquidity_qualified_count"] > row["eligible_universe_count"]:
        raise ValueError("liquidity-qualified count exceeds eligible universe")
    status = base._status(row)
    if status == "OK":
        scores = row["eligible_scores"]
        long_rank = row["long_ranking_desc"]
        short_rank = row["short_ranking_asc"]
        longs = row["preliminary_longs_10"]
        if not isinstance(scores, dict) or len(scores) != row["liquidity_qualified_count"]:
            raise ValueError("eligible_scores must cover every liquidity-qualified asset")
        for name, ranking in (("long_ranking_desc", long_rank), ("short_ranking_asc", short_rank)):
            if not isinstance(ranking, list) or len(ranking) != len(scores) or len(set(ranking)) != len(ranking):
                raise ValueError(f"{name} must be a unique full ranking")
            if set(ranking) != set(scores):
                raise ValueError(f"{name} and eligible_scores must cover the same assets")
        if not _monotone(long_rank, scores, True):
            raise ValueError("long_ranking_desc is not non-increasing by frozen score")
        if not _monotone(short_rank, scores, False):
            raise ValueError("short_ranking_asc is not non-decreasing by frozen score")
        if len(longs) != 10 or longs != long_rank[:10]:
            raise ValueError("preliminary_longs_10 must equal first 10 of frozen long ranking")
        risk = row["risk_state"]
        if not isinstance(risk, dict) or set(("exposure", "trailing_vol", "prior_weights")) - risk.keys():
            raise ValueError("risk_state requires exposure, trailing_vol and prior_weights")
        exposure = float(risk["exposure"])
        if not 0.0 < exposure <= 1.0:
            raise ValueError("risk_state exposure must be in (0,1]")
        if risk["trailing_vol"] is not None and float(risk["trailing_vol"]) <= 0:
            raise ValueError("risk_state trailing_vol must be positive or null")
        if not isinstance(risk["prior_weights"], dict):
            raise ValueError("risk_state prior_weights must be a mapping")
    else:
        for k in ("eligible_scores",):
            if row[k] not in ({}, None):
                raise ValueError("BLOCKED signal cannot carry synthetic scores")
        for k in ("long_ranking_desc", "short_ranking_asc", "preliminary_longs_10"):
            if row[k] not in ([], None):
                raise ValueError("BLOCKED signal cannot carry synthetic rankings/holdings")
    return base._stamp(row, "V16B_SIGNAL_SEAL", created)


def seal_signal(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    event = validate_signal_row(row, now=now)
    events = base.load_events(ledger)
    if any(e.get("event_type") == "V16B_SIGNAL_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("signal already sealed; append-only ledger forbids replacement")
    base.append_jsonl(ledger, event)
    return event


def _expected_turnover(signal_event: dict[str, Any], longs: list[str], shorts: list[str], exposure: float) -> float:
    weights = {a: 0.05 * exposure for a in longs}
    weights.update({a: -0.05 * exposure for a in shorts})
    prev = {str(k): float(v) for k, v in signal_event["risk_state"]["prior_weights"].items()}
    return sum(abs(weights.get(k, 0.0) - prev.get(k, 0.0)) for k in set(weights) | set(prev))


def validate_entry_row(row: dict[str, Any], signal_event: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    base._require_fields(row, ENTRY_REQUIRED)
    if signal_event["signal_date_utc"] != row["signal_date_utc"] or signal_event["entry_date_utc"] != row["entry_date_utc"]:
        raise ValueError("entry dates do not match signal seal")
    if row["signal_seal_sha256"] != signal_event["seal_sha256"]:
        raise ValueError("signal_seal_sha256 does not match sealed signal")
    entry = base.parse_date(row["entry_date_utc"])
    created = base._event_time(now)
    if created < base.parse_utc(signal_event["event_created_at_utc"]) or created >= base.close_after_day(entry):
        raise ValueError("entry seal must follow signal seal and be created before entry-day UTC close")
    base._require_hash(row["shortability_evidence_hash"], "shortability_evidence_hash")
    status = base._status(row)
    if status == "OK":
        if signal_event["status"] != "OK":
            raise ValueError("cannot create OK entry from BLOCKED signal")
        longs, shorts = row["longs_10"], row["shorts_10"]
        if longs != signal_event["preliminary_longs_10"]:
            raise ValueError("longs_10 cannot change after signal seal")
        if len(longs) != 10 or len(set(longs)) != 10 or len(shorts) != 10 or len(set(shorts)) != 10:
            raise ValueError("OK entry requires 10 unique longs and 10 unique shorts")
        if set(longs) & set(shorts):
            raise ValueError("same asset cannot be both long and short")
        long_exec = row["long_executability"]
        if not isinstance(long_exec, dict) or set(long_exec) != set(longs):
            raise ValueError("long_executability must cover exactly selected longs")
        if any(not isinstance(v, dict) or v.get("executable") is not True or not v.get("evidence_ref") for v in long_exec.values()):
            raise ValueError("all selected longs require positive predeclared executability evidence")
        checked = row["shortability_checked_ranked"]
        short_rank = signal_event["short_ranking_asc"]
        if not isinstance(checked, list) or not checked or len(checked) > len(short_rank):
            raise ValueError("invalid shortability_checked_ranked")
        selected = []
        for i, item in enumerate(checked):
            if not isinstance(item, dict) or item.get("asset") != short_rank[i] or "shortable" not in item or not item.get("evidence_ref"):
                raise ValueError("shortability checks must follow frozen ascending short ranking with evidence")
            if item["shortable"] is True:
                selected.append(item["asset"])
                if len(selected) == 10:
                    if i != len(checked) - 1:
                        raise ValueError("shortability checks must stop at the 10th short")
                    break
        if shorts != selected or len(selected) != 10:
            raise ValueError("shorts_10 must be first 10 causally shortable assets in frozen short ranking")
        instruments = row["entry_instruments"]
        if not isinstance(instruments, dict) or set(instruments) != set(longs) | set(shorts) or any(not isinstance(v, str) or not v for v in instruments.values()):
            raise ValueError("entry_instruments must map exactly all 20 selected assets")
        exposure = float(row["exposure"])
        frozen_exposure = float(signal_event["risk_state"]["exposure"])
        if abs(exposure - frozen_exposure) > TOL:
            raise ValueError("entry exposure must equal signal-sealed risk-state exposure")
        frozen_vol = signal_event["risk_state"]["trailing_vol"]
        if frozen_vol is None:
            if row["trailing_vol"] is not None:
                raise ValueError("entry trailing_vol must match signal risk state")
        elif abs(float(row["trailing_vol"]) - float(frozen_vol)) > TOL:
            raise ValueError("entry trailing_vol must equal signal-sealed risk state")
        expected_turnover = _expected_turnover(signal_event, longs, shorts, exposure)
        if abs(float(row["turnover_estimate"]) - expected_turnover) > 1e-10:
            raise ValueError("turnover_estimate inconsistent with sealed prior/current weights")
        if abs(float(row["transaction_cost_bps"]) - COST_BPS) > TOL:
            raise ValueError("transaction_cost_bps must equal frozen 15 bps")
    else:
        for k in ("exposure", "trailing_vol", "turnover_estimate", "transaction_cost_bps"):
            if row[k] is not None:
                raise ValueError(f"BLOCKED entry must not carry synthetic field {k}")
        if row["longs_10"] not in ([], None) or row["shorts_10"] not in ([], None) or row["entry_instruments"] not in ({}, None):
            raise ValueError("BLOCKED entry cannot carry synthetic holdings")
    return base._stamp(row, "V16B_ENTRY_SEAL", created)


def seal_entry(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    events = base.load_events(ledger)
    sig = base._unique_stage(events, "V16B_SIGNAL_SEAL", row.get("signal_date_utc", ""))
    event = validate_entry_row(row, sig, now=now)
    if any(e.get("event_type") == "V16B_ENTRY_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("entry already sealed; append-only ledger forbids replacement")
    base.append_jsonl(ledger, event)
    return event


def seal_result(input_path: Path, ledger: Path, now: datetime | None = None) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    events = base.load_events(ledger)
    entry = base._unique_stage(events, "V16B_ENTRY_SEAL", row.get("signal_date_utc", ""))
    event = base.validate_result_row(row, entry, now=now)
    if any(e.get("event_type") == "V16B_RESULT_SEAL" and e.get("signal_date_utc") == event["signal_date_utc"] for e in events):
        raise ValueError("result already sealed; append-only ledger forbids replacement")
    base.append_jsonl(ledger, event)
    return event


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("seal-signal", "seal-entry", "seal-result"):
        a = sub.add_parser(name); a.add_argument("--input", required=True); a.add_argument("--ledger", required=True)
    d = sub.add_parser("attach-delta")
    d.add_argument("--signal-date", required=True); d.add_argument("--delta-print", required=True, type=float)
    d.add_argument("--source-timestamp", required=True); d.add_argument("--source-ref", required=True); d.add_argument("--ledger", required=True)
    a = p.parse_args()
    if a.cmd == "seal-signal": event = seal_signal(Path(a.input), Path(a.ledger))
    elif a.cmd == "seal-entry": event = seal_entry(Path(a.input), Path(a.ledger))
    elif a.cmd == "seal-result": event = seal_result(Path(a.input), Path(a.ledger))
    else: event = base.attach_delta(a.signal_date, a.delta_print, a.source_timestamp, a.source_ref, Path(a.ledger))
    print(json.dumps({"status":"PASS","event_type":event["event_type"],"seal_sha256":event["seal_sha256"],"ORDERS":0,"REAL_CAPITAL":0,"ENGINE_FEED":False}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
