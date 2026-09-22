#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc
WIN_RE = re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$")
OHLC_FEATURES = {
    "OPEN_RETURN", "OPEN_RANGE", "REALIZED_VOL", "BAR_IMBALANCE",
    "CLOSE_LOCATION", "BODY_RANGE", "GAP_FROM_PRIOR_CLOSE",
}
VOLUME_FEATURE = "VOLUME_EARLY"
EXPECTED_ELIGIBLE = 580


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_win_info(info) -> bool:
    name = str(getattr(info, "name", ""))
    desc = str(getattr(info, "description", "")).upper()
    path = str(getattr(info, "path", "")).upper()
    return bool(WIN_RE.fullmatch(name)) and "IBOVESPA MINI" in desc and ("BVMF" in path or "B3" in path)


def meta(info) -> dict:
    return {
        "symbol": str(info.name),
        "description": str(getattr(info, "description", "")),
        "path": str(getattr(info, "path", "")),
        "expiration_time": int(getattr(info, "expiration_time", 0) or 0),
        "trade_mode": int(getattr(info, "trade_mode", 0) or 0),
    }


def expiry_local(m: dict) -> date | None:
    epoch = int(m.get("expiration_time") or 0)
    if epoch <= 0:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC).astimezone(TZ).date()


def choose_contract(session: date, metas: list[dict]) -> dict | None:
    candidates = []
    for m in metas:
        exp = expiry_local(m)
        if exp is not None and exp >= session:
            candidates.append((m["expiration_time"], m["symbol"], m))
    return sorted(candidates, key=lambda x: (x[0], x[1]))[0][2] if candidates else None


def decode_epoch(epoch: int, mode: str) -> datetime:
    if mode == "UTC_EPOCH":
        return datetime.fromtimestamp(epoch, tz=UTC).astimezone(TZ)
    if mode == "BROKER_LOCAL_EPOCH":
        return datetime.fromtimestamp(epoch, tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
    raise RuntimeError(f"UNKNOWN_TIME_MODE:{mode}")


def detect_time_mode(mt5, symbol: str, now: datetime) -> tuple[str | None, dict]:
    tick = mt5.symbol_info_tick(symbol)
    epoch = int(getattr(tick, "time", 0) or 0) if tick else 0
    if epoch <= 0:
        return None, {"raw_tick_epoch": epoch, "reason": "NO_TICK_EPOCH"}
    utc_dt = datetime.fromtimestamp(epoch, tz=UTC).astimezone(TZ)
    local_dt = datetime.fromtimestamp(epoch, tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
    du = abs((now - utc_dt).total_seconds())
    dl = abs((now - local_dt).total_seconds())
    mode = "UTC_EPOCH" if du <= dl else "BROKER_LOCAL_EPOCH"
    delta = min(du, dl)
    return mode, {
        "raw_tick_epoch": epoch,
        "utc_interpretation": utc_dt.isoformat(),
        "broker_local_interpretation": local_dt.isoformat(),
        "selected_mode": mode,
        "freshness_seconds": delta,
        "fresh_within_900s": delta <= 900,
    }


def next_b3_weekday(d: date) -> date:
    x = d + timedelta(days=1)
    while x.weekday() >= 5:
        x += timedelta(days=1)
    return x


def raw_rate(r) -> dict:
    return {
        "epoch": int(r["time"]),
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
        "tick_volume": int(r["tick_volume"]),
        "spread": int(r["spread"]),
        "real_volume": int(r["real_volume"]),
    }


def normalize(rows, mode: str) -> list[dict]:
    out = []
    if rows is None:
        return out
    for r in rows:
        x = raw_rate(r)
        dt = decode_epoch(x["epoch"], mode)
        out.append({"timestamp": dt.isoformat(), **x})
    return sorted(out, key=lambda x: x["timestamp"])


def closed_session_rows(rows: list[dict], session: date, now: datetime) -> list[dict]:
    start = datetime(session.year, session.month, session.day, 9, 0, tzinfo=TZ)
    closed_before = now.replace(second=0, microsecond=0)
    closed_before -= timedelta(minutes=closed_before.minute % 5)
    # A bar stamped T is closed only once the next 5-minute boundary is reached.
    out = []
    for r in rows:
        ts = datetime.fromisoformat(r["timestamp"])
        if start <= ts and ts + timedelta(minutes=5) <= closed_before:
            out.append(r)
    return out


def session_dates(rows: list[dict]) -> list[str]:
    return sorted({r["timestamp"][:10] for r in rows})


def ohlc_integrity(rows: list[dict]) -> bool:
    for r in rows:
        o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
        if not (math.isfinite(o) and math.isfinite(h) and math.isfinite(l) and math.isfinite(c)):
            return False
        if l > min(o, c) or h < max(o, c) or l > h:
            return False
        for px in (o, h, l, c):
            q = px / 5.0
            if abs(q - round(q)) > 1e-7 * max(1.0, abs(q)):
                return False
    return True


def exact_spacing(rows: list[dict]) -> bool:
    ts = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    return len(ts) >= 2 and all(int((b - a).total_seconds()) == 300 for a, b in zip(ts, ts[1:]))


def eligible_population(item3: dict) -> list[dict]:
    rows = [x for x in item3["autonomous_base"]["families"] if x.get("experimental_shadow_eligible") is True]
    if len(rows) != EXPECTED_ELIGIBLE:
        raise RuntimeError(f"ELIGIBLE_COUNT_MISMATCH:{len(rows)}:{EXPECTED_ELIGIBLE}")
    ids = [x["family_id"] for x in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError("DUPLICATE_ELIGIBLE_FAMILY_IDS")
    return sorted(rows, key=lambda x: int(str(x["family_id"])[1:]))


def family_contract(row: dict) -> dict:
    lookback = int(row.get("standardization_lookback_sessions") or 20)
    return {
        "family_id": row["family_id"],
        "feature": row["feature"],
        "direction": row["direction"],
        "decision_window_minutes": int(row["decision_window_minutes"]),
        "abs_z_threshold": float(row["abs_z_threshold"]),
        "holding_horizons_minutes": [30, 60, 120],
        "standardization_lookback_sessions": lookback,
        "causal_standardization": f"ROLLING_{lookback}_PRIOR_SESSIONS_MEDIAN_MAD",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    runtime_root = Path(args.runtime_root)
    prereg = load(Path(args.prereg))
    if prereg.get("status") != "PREREGISTERED_BEFORE_PHYSICAL_FORWARD_SOURCE_READ":
        raise RuntimeError("PREREG_STATUS_MISMATCH")

    item3_path = runtime_root / prereg["activation_population"]["canonical_item3_path"]
    item3 = load(item3_path)
    pop = eligible_population(item3)
    source_sha256 = sha256_file(item3_path)

    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    try:
        now = datetime.now(TZ)
        term = mt5.terminal_info()
        acct = mt5.account_info()
        if term is None or not bool(getattr(term, "connected", False)):
            raise RuntimeError("MT5_TERMINAL_NOT_CONNECTED")
        metas = sorted([meta(x) for x in list(mt5.symbols_get(group="WIN*") or []) if exact_win_info(x)], key=lambda x: x["symbol"])
        if not metas:
            raise RuntimeError("NO_EXACT_WIN_CONTRACTS")
        selected = choose_contract(now.date(), metas)
        if selected is None:
            raise RuntimeError("NO_NONEXPIRED_EXACT_WIN_CONTRACT")
        symbol = selected["symbol"]
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"SYMBOL_SELECT_FAILED:{symbol}:{mt5.last_error()}")
        mode, tick_ev = detect_time_mode(mt5, symbol, now)
        if mode is None:
            raise RuntimeError("TIME_MODE_UNRESOLVED")

        rr = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 3000)
        err = mt5.last_error()
        rows = normalize(rr, mode)
        today = closed_session_rows(rows, now.date(), now)
        dates = session_dates(rows)
        previous_dates = [d for d in dates if d < now.date().isoformat()]
        previous_date = previous_dates[-1] if previous_dates else None
        previous_rows = [r for r in rows if previous_date and r["timestamp"].startswith(previous_date)]

        time_ok = bool(tick_ev.get("fresh_within_900s"))
        bars_ok = len(today) >= 40 and exact_spacing(today)
        ohlc_ok = bool(today) and ohlc_integrity(today)
        prior_close_ok = bool(previous_rows) and ohlc_integrity(previous_rows)
        ohlc_source_pass = time_ok and bars_ok and ohlc_ok and prior_close_ok
        positive_real = sum(int(r["real_volume"]) > 0 for r in today)
        real_fraction = positive_real / len(today) if today else 0.0
        volume_pass = ohlc_source_pass and real_fraction >= float(prereg["volume_admission"]["minimum_positive_real_volume_bar_fraction"])

        feature_qa = {f: ohlc_source_pass for f in sorted(OHLC_FEATURES)}
        feature_qa[VOLUME_FEATURE] = volume_pass
        active, waiting = [], []
        for row in pop:
            contract = family_contract(row)
            rec = {
                "family_id": row["family_id"],
                "contract": contract,
                "origin_classification": row["classification"],
                "historical_credit": 0,
                "promotion_authority": False,
            }
            if feature_qa.get(contract["feature"], False):
                active.append(rec)
            else:
                rec["wait_reason"] = "PROSPECTIVE_SOURCE_SEMANTICS_NOT_QUALIFIED_FOR_FEATURE"
                waiting.append(rec)

        raw_evidence = {
            "captured_at": now.isoformat(),
            "terminal": {
                "name": str(getattr(term, "name", "")),
                "company": str(getattr(term, "company", "")),
                "connected": bool(getattr(term, "connected", False)),
                "server": str(getattr(acct, "server", "")) if acct else "",
            },
            "selected_contract": selected,
            "selected_contract_expiration_local": str(expiry_local(selected)),
            "enumerated_exact_win_contract_count": len(metas),
            "time_evidence": tick_ev,
            "copy_rates_error": str(err),
            "closed_session_bar_count": len(today),
            "closed_session_first": today[0]["timestamp"] if today else None,
            "closed_session_last": today[-1]["timestamp"] if today else None,
            "exact_300s_spacing": exact_spacing(today) if today else False,
            "ohlc_tick_grid_integrity": ohlc_ok,
            "previous_session_date_observed": previous_date,
            "previous_session_close_observable": prior_close_ok,
            "positive_real_volume_bars": positive_real,
            "positive_real_volume_fraction": real_fraction,
            "tick_volume_not_used_as_real_volume": True,
            "raw_today_rows": today,
        }
        raw_hash = hashlib.sha256(json.dumps(raw_evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        raw_evidence["raw_evidence_sha256"] = raw_hash

        binding = {
            "schema": "gate_btc_2.factory_item3b_forward_source_binding.v1",
            "status": "FORWARD_SOURCE_BOUND" if active else "FORWARD_SOURCE_FAIL_CLOSED",
            "captured_at": now.isoformat(),
            "canonical_item3_sha256": source_sha256,
            "canonical_item3_git_blob_sha_expected": prereg["activation_population"]["canonical_item3_git_blob_sha"],
            "eligible_population_count": len(pop),
            "selected_symbol": symbol,
            "roll_rule": prereg["prospective_source"]["current_contract_rule"],
            "source_role": prereg["prospective_source"]["source_role"],
            "feature_source_qa": feature_qa,
            "ohlc_source_pass": ohlc_source_pass,
            "volume_source_pass": volume_pass,
            "volume_positive_real_fraction": real_fraction,
            "active_family_count": len(active),
            "waiting_source_semantics_count": len(waiting),
            "d0": next_b3_weekday(now.date()).isoformat() if active else None,
            "raw_evidence_sha256": raw_hash,
            "survivor_credit": 0,
            "promotion_authority": False,
            "historical_backfill_credit": 0,
            "safety": prereg["safety"],
        }
        manifest = {
            "schema": "gate_btc_2.factory_item3b_experimental_activation_manifest.v1",
            "status": "ACTIVATED_PENDING_FIRST_OBSERVATION" if active else "BLOCKED_SOURCE_BINDING",
            "experimental_status": "EXPERIMENTAL_PROSPECTIVE_SHADOW",
            "d0": binding["d0"],
            "activation_population_rule": "ALL_CANONICAL_ITEM3_ELIGIBLE_FAMILIES_WITH_FEATURE_SOURCE_QA_PASS",
            "eligible_before_source_qa": len(pop),
            "active_family_count": len(active),
            "waiting_source_semantics_count": len(waiting),
            "active_families": active,
            "waiting_families": waiting,
            "source_binding_sha256": hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
            "historical_credit": 0,
            "retroactive_credit": 0,
            "promotion_authority": False,
            "direct_survivor_transition": False,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_backfill": True,
            "no_retune": True,
        }

        out = Path(args.out_dir)
        dump(out / "RAW_FORWARD_SOURCE_EVIDENCE.json", raw_evidence)
        dump(out / "FORWARD_SOURCE_BINDING.json", binding)
        dump(out / "ACTIVATION_MANIFEST.json", manifest)
        print(json.dumps({
            "status": binding["status"],
            "symbol": symbol,
            "eligible": len(pop),
            "active": len(active),
            "waiting": len(waiting),
            "ohlc_source_pass": ohlc_source_pass,
            "volume_source_pass": volume_pass,
            "d0": binding["d0"],
        }, sort_keys=True))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
