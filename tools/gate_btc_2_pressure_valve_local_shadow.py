#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gate_btc_2_item3b_forward_source_probe as source
import gate_btc_2_item3c_forward_collector as item3c

TZ = ZoneInfo("America/Sao_Paulo")
FORBIDDEN_ROOT = Path(r"C:\actions-runner\qrds-local-shadow")
DEFAULT_ROOT = Path(r"C:\actions-runner\qrds-pressure-valve-shadow")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def assert_isolation(root: Path) -> None:
    a = str(root.resolve()).lower().rstrip("\\/")
    b = str(FORBIDDEN_ROOT).lower().rstrip("\\/")
    if a == b or a.startswith(b + "\\") or a.startswith(b + "/"):
        raise RuntimeError("ISOLATION_FAIL_FORBIDDEN_H1_H31_ROOT")


def previous_close(records: list[dict]) -> float | None:
    for rec in reversed(records):
        value = rec.get("session_close")
        if isinstance(value, (int, float)) and float(value) > 0:
            return float(value)
    return None


def prior_records(ledger: Path, session: str) -> list[dict]:
    out = []
    for p in sorted(ledger.glob("*.json")) if ledger.exists() else []:
        if p.stem >= session:
            continue
        try:
            rec = load(p)
        except Exception:
            continue
        if rec.get("session") == p.stem and rec.get("record_sha256"):
            out.append(rec)
    return out


def histories(records: list[dict]) -> dict[str, list[float]]:
    return item3c.histories(records)


def wait(status: str, now: datetime, **extra):
    return {
        "schema": "gate_btc_2.pressure_valve_local_shadow_status.v1",
        "status": status,
        "checked_at": now.isoformat(),
        "monitoring_mirror_only": True,
        "scientific_credit": 0,
        "survivor_credit": 0,
        "promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        **extra,
    }


def aggregate_economics(records: list[dict], family_ids: list[str]) -> dict:
    families = {}
    for fid in family_ids:
        families[fid] = {
            "family_id": fid,
            "trigger_sessions": 0,
            "horizons": {
                str(h): {"trades": 0, "gross_bps": 0.0, "net_ref_2bps": 0.0, "net_stress_3bps": 0.0, "delayed_net_ref_2bps": 0.0}
                for h in (30, 60, 120)
            },
        }
    for rec in records:
        for row in rec.get("family_observations", []):
            fid = row.get("family_id")
            if fid not in families or row.get("state") != "TRIGGER":
                continue
            families[fid]["trigger_sessions"] += 1
            for outcome in row.get("outcomes", []):
                h = str(int(outcome["horizon_minutes"]))
                slot = families[fid]["horizons"][h]
                slot["trades"] += 1
                for key in ("gross_bps", "net_ref_2bps", "net_stress_3bps"):
                    slot[key] += float(outcome[key])
                delayed = outcome.get("delayed_net_ref_2bps")
                if delayed is not None:
                    slot["delayed_net_ref_2bps"] += float(delayed)
    return {
        "schema": "gate_btc_2.pressure_valve_economics.v1",
        "monitoring_mirror_only": True,
        "scientific_credit": 0,
        "families": [families[fid] for fid in family_ids],
    }


def self_test() -> None:
    assert_isolation(DEFAULT_ROOT)
    try:
        assert_isolation(FORBIDDEN_ROOT / "pressure_valves")
    except RuntimeError:
        pass
    else:
        raise AssertionError("forbidden root isolation test failed")
    cfg = {
        "family_id": "H626",
        "feature": "BODY_RANGE",
        "direction": "CONTINUATION",
        "decision_window_minutes": 60,
        "abs_z_threshold": 0.75,
        "standardization_lookback_sessions": 10,
        "holding_horizons_minutes": [30, 60, 120],
    }
    rows = []
    base = datetime(2026, 9, 23, 9, 0, tzinfo=TZ)
    for i in range(50):
        px = 100000.0 + i * 10.0
        rows.append({"timestamp": base.isoformat(), "open": px, "high": px + 20, "low": px - 20, "close": px + 10, "real_volume": 100 + i})
    x = item3c.raw_feature("BODY_RANGE", rows, 60, None)
    assert x is not None
    result = item3c.evaluate_family(cfg, rows, x, [x * f for f in (0.2,0.3,0.4,0.5,0.6,1.4,1.5,1.6,1.7,1.8)])
    assert result["family_id"] == "H626"
    assert result["survivor_credit"] == 0
    assert result["promotion_authority"] is False
    print("PRESSURE_VALVE_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.config:
        raise SystemExit("--config is required")

    root = Path(args.root)
    assert_isolation(root)
    cfg = load(Path(args.config))
    now = datetime.now(TZ)
    session = now.date().isoformat()
    spool = root / "spool" / "pressure_valves"
    ledger = spool / "ledger"
    status_path = spool / "STATUS.json"
    economics_path = spool / "ECONOMICS.json"
    snapshot_path = spool / "DAILY_SNAPSHOT.json"

    if cfg.get("status") != "MONITORING_MIRROR_ONLY":
        raise RuntimeError("CONFIG_STATUS_MISMATCH")
    if session < str(cfg["d0"]):
        dump(status_path, wait("WAIT_D0", now, d0=cfg["d0"], session=session))
        return 0
    if now.weekday() >= 5:
        dump(status_path, wait("WAIT_B3_WEEKDAY", now, session=session))
        return 0
    hh, mm = map(int, cfg["schedule"]["not_before_local"].split(":"))
    if now < now.replace(hour=hh, minute=mm, second=0, microsecond=0):
        dump(status_path, wait("WAIT_DAILY_BATCH_WINDOW", now, session=session))
        return 0

    target = ledger / f"{session}.json"
    if target.exists():
        recs = prior_records(ledger, "9999-99-99")
        dump(economics_path, aggregate_economics(recs, [x["family_id"] for x in cfg["families"]]))
        existing = load(target)
        dump(status_path, wait("IDEMPOTENT_ALREADY_COLLECTED", now, session=session, record_sha256=existing.get("record_sha256")))
        return 0

    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    try:
        term = mt5.terminal_info()
        if term is None or not bool(getattr(term, "connected", False)):
            raise RuntimeError("MT5_TERMINAL_NOT_CONNECTED")
        metas = sorted([source.meta(x) for x in list(mt5.symbols_get(group="WIN*") or []) if source.exact_win_info(x)], key=lambda x: x["symbol"])
        selected = source.choose_contract(now.date(), metas)
        if selected is None:
            raise RuntimeError("NO_NONEXPIRED_EXACT_WIN_CONTRACT")
        symbol = selected["symbol"]
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"SYMBOL_SELECT_FAILED:{symbol}:{mt5.last_error()}")
        raw = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 3000)
        err = mt5.last_error()
        rows = source.closed_session_rows(source.normalize(raw, cfg["source"]["time_mode"]), now.date(), now)
    finally:
        mt5.shutdown()

    max_window = max(int(c["decision_window_minutes"]) for c in cfg["families"])
    if not item3c.enough_session_rows(rows, max_window):
        raise RuntimeError(f"INCOMPLETE_SESSION_FOR_FROZEN_OUTCOMES bars={len(rows)} max_window={max_window}")
    if not source.exact_spacing(rows):
        raise RuntimeError("SESSION_M5_SPACING_FAIL")
    if not source.ohlc_integrity(rows):
        raise RuntimeError("SESSION_OHLC_TICK_GRID_FAIL")

    priors = prior_records(ledger, session)
    hist = histories(priors)
    prior_close = previous_close(priors)
    keys = sorted({item3c.feature_key(c["feature"], c["decision_window_minutes"]) for c in cfg["families"]})
    values = {}
    feature_rows = []
    for key in keys:
        feature, window = key.split("|", 1)
        value = item3c.raw_feature(feature, rows, int(window), prior_close)
        available = value is not None and math.isfinite(float(value))
        values[key] = float(value) if available else None
        feature_rows.append({"key": key, "feature": feature, "decision_window_minutes": int(window), "available": available, "value": values[key]})

    family_rows = []
    for contract in cfg["families"]:
        key = item3c.feature_key(contract["feature"], contract["decision_window_minutes"])
        family_rows.append(item3c.evaluate_family(contract, rows, values[key], hist.get(key, [])))
    counts = {}
    for row in family_rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1

    record = {
        "schema": "gate_btc_2.pressure_valve_local_shadow_session.v1",
        "session": session,
        "captured_at": now.isoformat(),
        "monitoring_mirror_only": True,
        "source": {"provider": "LOCAL_SELF_HOSTED_MT5_TERMINAL", "symbol": symbol, "time_mode": cfg["source"]["time_mode"], "copy_rates_error": str(err), "bar_count": len(rows), "first_bar": rows[0]["timestamp"], "last_bar": rows[-1]["timestamp"]},
        "feature_observations": feature_rows,
        "family_observations": family_rows,
        "family_state_counts": counts,
        "session_close": float(rows[-1]["close"]),
        "scientific_credit": 0,
        "survivor_credit": 0,
        "promotion_authority": False,
        "canonical_prospective_ledger": "Item3C only",
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True
    }
    record["record_sha256"] = item3c.stable_hash(record)
    dump(target, record)
    dump(snapshot_path, record)
    all_records = priors + [record]
    dump(economics_path, aggregate_economics(all_records, [x["family_id"] for x in cfg["families"]]))
    dump(status_path, wait("SESSION_CAPTURED_MONITOR_ONLY", now, session=session, symbol=symbol, family_state_counts=counts, record_sha256=record["record_sha256"], prior_forward_sessions=len(priors)))
    print(json.dumps({"session": session, "symbol": symbol, "states": counts, "record_sha256": record["record_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
