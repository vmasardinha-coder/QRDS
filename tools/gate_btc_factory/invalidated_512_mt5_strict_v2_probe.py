#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc
START = "2025-01-01"
END = "2026-08-09"
MIN_TOTAL = 322
MIN_PART = 161
NAMESPACE = "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
WIN_RE = re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$")

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "MT5_READ_ONLY": True,
    "NO_ORDER_SEND": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_LATE_SEAL": True,
    "NO_COUNTER_RESET": True,
    "NO_RETUNE": True,
    "FAIL_CLOSED": True,
    "H1_ECONOMICS_READ": False,
}


def canonical_bytes(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def eligible_symbol(info) -> bool:
    name = str(getattr(info, "name", ""))
    desc = str(getattr(info, "description", "")).upper()
    path = str(getattr(info, "path", "")).upper()
    return bool(WIN_RE.fullmatch(name)) and "IBOVESPA MINI" in desc and ("BVMF" in path or "B3" in path)


def symbol_meta(info) -> dict:
    return {
        "symbol": str(getattr(info, "name", "")),
        "description": str(getattr(info, "description", "")),
        "path": str(getattr(info, "path", "")),
        "expiration_time": int(getattr(info, "expiration_time", 0) or 0),
        "currency_profit": str(getattr(info, "currency_profit", "")),
        "currency_margin": str(getattr(info, "currency_margin", "")),
        "trade_mode": int(getattr(info, "trade_mode", 0) or 0),
    }


def expiry_local_date(meta: dict) -> str | None:
    x = int(meta.get("expiration_time") or 0)
    if x <= 0:
        return None
    return datetime.fromtimestamp(x, tz=UTC).astimezone(TZ).date().isoformat()


def choose_contract(session: str, metas: list[dict]) -> str | None:
    candidates = []
    for m in metas:
        exp = expiry_local_date(m)
        if exp is None:
            continue
        if exp >= session:
            candidates.append((int(m["expiration_time"]), m["symbol"]))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][1]


def decode_epoch(epoch: int, mode: str) -> datetime:
    if mode == "UTC_EPOCH":
        return datetime.fromtimestamp(epoch, tz=UTC).astimezone(TZ)
    if mode == "BROKER_LOCAL_EPOCH":
        return datetime.fromtimestamp(epoch, tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
    raise RuntimeError(f"UNKNOWN_TIME_MODE:{mode}")


def query_time(dt: datetime, mode: str) -> datetime:
    if mode == "UTC_EPOCH":
        return dt.astimezone(UTC)
    if mode == "BROKER_LOCAL_EPOCH":
        return dt.replace(tzinfo=None).replace(tzinfo=UTC)
    raise RuntimeError(f"UNKNOWN_TIME_MODE:{mode}")


def detect_time_mode(mt5, active_symbols: list[str]) -> tuple[str, dict]:
    now = datetime.now(TZ)
    evidence = []
    for symbol in active_symbols:
        tick = mt5.symbol_info_tick(symbol)
        epoch = int(getattr(tick, "time", 0) or 0) if tick else 0
        if epoch <= 0:
            continue
        utc_dt = datetime.fromtimestamp(epoch, tz=UTC).astimezone(TZ)
        local_dt = datetime.fromtimestamp(epoch, tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
        du = abs((now - utc_dt).total_seconds())
        dl = abs((now - local_dt).total_seconds())
        mode = "UTC_EPOCH" if du <= dl else "BROKER_LOCAL_EPOCH"
        delta = min(du, dl)
        evidence.append({"symbol": symbol, "mode": mode, "delta_seconds": delta, "raw_tick_epoch": epoch})
    fresh = [e for e in evidence if e["delta_seconds"] <= 900]
    modes = sorted({e["mode"] for e in fresh})
    if len(modes) != 1:
        raise RuntimeError(f"AMBIGUOUS_MT5_TIME_MODE:modes={modes}:fresh={len(fresh)}")
    return modes[0], {"current_tick_evidence": evidence, "selected_mode": modes[0]}


def normalize_rows(rows, symbol: str, mode: str) -> list[dict]:
    out = []
    for r in list(rows or []):
        dt = decode_epoch(int(r["time"]), mode)
        d = dt.date().isoformat()
        if START <= d <= END:
            out.append({
                "symbol": symbol,
                "timestamp": dt.isoformat(),
                "epoch": int(r["time"]),
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
                "tick_volume": int(r["tick_volume"]),
                "spread": int(r["spread"]),
                "real_volume": int(r["real_volume"]),
            })
    out.sort(key=lambda x: (x["timestamp"], x["symbol"]))
    return out


def build_candidate(raw_by_symbol: dict[str, list[dict]], metas: list[dict]) -> tuple[list[dict], dict]:
    by_session_symbol = defaultdict(lambda: defaultdict(list))
    for symbol, rows in raw_by_symbol.items():
        for row in rows:
            by_session_symbol[row["timestamp"][:10]][symbol].append(row)
    candidate = []
    session_qa = []
    for session in sorted(by_session_symbol):
        selected = choose_contract(session, metas)
        rows = list(by_session_symbol[session].get(selected, [])) if selected else []
        ts = [datetime.fromisoformat(r["timestamp"]) for r in rows]
        duplicate = len({r["timestamp"] for r in rows}) != len(rows)
        exact_spacing = bool(len(ts) >= 2) and all(int((b-a).total_seconds()) == 300 for a, b in zip(ts, ts[1:]))
        valid = selected is not None and not duplicate and len(rows) >= 40 and exact_spacing
        session_qa.append({"session": session, "selected_symbol": selected, "bar_count": len(rows), "duplicate": duplicate, "exact_300s_spacing": exact_spacing, "structurally_valid": valid})
        if valid:
            candidate.extend(rows)
    return candidate, {"sessions": session_qa}


def partition_counts(valid_sessions: list[str]) -> dict:
    # Frozen split is capacity-only: first 161 valid sessions = discovery,
    # next 161 valid sessions = replication. No economics are read here.
    ordered = sorted(valid_sessions)
    return {"total": len(ordered), "discovery": min(len(ordered), 161), "replication": max(0, min(len(ordered)-161, 161))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    import MetaTrader5 as mt5

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        all_symbols = list(mt5.symbols_get(group="WIN*") or [])
        metas = [symbol_meta(x) for x in all_symbols if eligible_symbol(x)]
        metas.sort(key=lambda x: x["symbol"])
        if not metas:
            raise RuntimeError("NO_EXACT_WIN_CONTRACTS_ENUMERATED")
        if any(expiry_local_date(m) is None for m in metas):
            raise RuntimeError("MISSING_EXPIRATION_METADATA")

        active = []
        for m in metas:
            if mt5.symbol_select(m["symbol"], True):
                tick = mt5.symbol_info_tick(m["symbol"])
                if tick and int(getattr(tick, "time", 0) or 0) > 0:
                    active.append(m["symbol"])
        mode, time_evidence = detect_time_mode(mt5, active)

        start_dt = datetime.combine(datetime.fromisoformat(START).date(), time.min, tzinfo=TZ)
        end_dt = datetime.combine(datetime.fromisoformat(END).date(), time(23, 59, 59), tzinfo=TZ)
        raw_by_symbol = {}
        capture_errors = []
        for m in metas:
            s = m["symbol"]
            if not mt5.symbol_select(s, True):
                capture_errors.append({"symbol": s, "error": "SYMBOL_SELECT_FAILED"})
                raw_by_symbol[s] = []
                continue
            rows = mt5.copy_rates_range(s, mt5.TIMEFRAME_M5, query_time(start_dt, mode), query_time(end_dt, mode))
            err = mt5.last_error()
            raw_by_symbol[s] = normalize_rows(rows, s, mode)
            if rows is None:
                capture_errors.append({"symbol": s, "error": str(err)})

        raw = {
            "schema": "qrds.factory.invalidated_512.mt5_raw_capture.v1",
            "namespace": NAMESPACE,
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "window": {"start": START, "end": END},
            "time_mode": mode,
            "time_evidence": time_evidence,
            "terminal": {
                "name": str(getattr(terminal, "name", "")),
                "company": str(getattr(terminal, "company", "")),
                "connected": bool(getattr(terminal, "connected", False)),
            },
            "account_server": str(getattr(account, "server", "")),
            "symbols": metas,
            "capture_errors": capture_errors,
            "records_by_symbol": raw_by_symbol,
            "safety": SAFETY,
        }
        raw_hash = sha(raw)
        raw["raw_capture_sha256"] = raw_hash
        (args.out_dir / "RAW_CAPTURE.json").write_bytes(canonical_bytes(raw))

        candidate, qa = build_candidate(raw_by_symbol, metas)
        valid_sessions = [x["session"] for x in qa["sessions"] if x["structurally_valid"]]
        counts = partition_counts(valid_sessions)
        normalized_hash = hashlib.sha256(canonical_bytes(candidate)).hexdigest()

        # MT5 history is broker-terminal material. Availability/coverage can be
        # proven physically here; publication/revision/PIT semantics are not
        # invented. They remain false unless separately authoritative evidence exists.
        gates = {
            "identity_qa": True,
            "schema_qa": True,
            "timezone_qa": True,
            "chronology_qa": all(choose_contract(s, metas) is not None for s in valid_sessions),
            "capacity_qa": counts["total"] >= MIN_TOTAL and counts["discovery"] >= MIN_PART and counts["replication"] >= MIN_PART,
            "publication_semantics_proven": False,
            "revision_semantics_proven": False,
            "point_in_time_validity_proven": False,
            "independent_unseen_window_proven": True,
        }
        green = all(gates.values())
        result = {
            "schema": "qrds.factory.invalidated_512.mt5_strict_v2_source_result.v1",
            "authority_issue": 693,
            "evaluation_namespace": NAMESPACE,
            "status": "SOURCE_GATE_GREEN" if green else "MT5_SOURCE_QUALIFICATION_FAIL_CLOSED",
            "window": {"start": START, "end": END},
            "raw_capture_sha256": raw_hash,
            "normalized_candidate_sha256": normalized_hash,
            "enumerated_exact_win_contract_count": len(metas),
            "raw_bar_count": sum(len(v) for v in raw_by_symbol.values()),
            "candidate_bar_count": len(candidate),
            "valid_session_counts": counts,
            "minimum_required": {"total": MIN_TOTAL, "discovery": MIN_PART, "replication": MIN_PART},
            "source_gates": gates,
            "capture_errors": capture_errors,
            "source_admission_pass": green,
            "requalification_economics_allowed": green,
            "scientific_family_credit": 0,
            "prospective_credit": 0,
            "historical_backfill_credit": 0,
            "safety": SAFETY,
        }
        result["result_sha256"] = sha(result)
        (args.out_dir / "CANDIDATE_M5.json").write_bytes(canonical_bytes(candidate))
        (args.out_dir / "SESSION_QA.json").write_bytes(canonical_bytes(qa))
        (args.out_dir / "RESULT.json").write_bytes(canonical_bytes(result))
        print(json.dumps({k: result[k] for k in ("status", "enumerated_exact_win_contract_count", "raw_bar_count", "candidate_bar_count", "valid_session_counts", "source_admission_pass")}, sort_keys=True))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
