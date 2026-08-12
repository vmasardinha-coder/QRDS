#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

from gate_btc_b3_h1_parser import process_zip, URL

TZ = "America/Sao_Paulo"
UPSTREAM_ENGINE_SHA256 = "1e313614e4f8dd318488e3abdde1d56848c076f9e57bb47a4fd5ce4f9c06410c"
FULL_FROZEN_SCHEDULE_SHA256 = "5fd7314f55fb1c6394628d94227fdc0ed375016a57453a07f05828ffd5a9282f"
H1_PREFIX_SHA256 = "c9ff28b4d1b6c8e2aceb3281da51bc41858780493c99a0eeac148f2bdd0bc4f6"
BLIND_LOCK_SHA256 = "ceb5ed9b48f2c4f616eee82a78942f39deceb41272369be02ad207b49425cbf1"
EXPECTED_M5 = 102
TICK = {"WIN": 5.0, "WDO": 0.5}
SCHEDULE_PREFIX = """date,WIN,WDO,freeze_status
2026-08-10,WINQ26,WDOU26,FROZEN_BEFORE_H1
2026-08-11,WINQ26,WDOU26,FROZEN_BEFORE_H1
2026-08-12,WINQ26,WDOU26,FROZEN_BEFORE_H1
2026-08-13,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-14,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-17,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-18,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-19,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-20,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-21,WINV26,WDOU26,FROZEN_BEFORE_H1
2026-08-24,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-08-25,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-08-26,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-08-27,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-08-28,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-08-31,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-09-01,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-09-02,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-09-03,WINV26,WDOV26,FROZEN_BEFORE_H1
2026-09-04,WINV26,WDOV26,FROZEN_BEFORE_H1
"""


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_schedule() -> dict[str, dict[str, str]]:
    if hashlib.sha256(SCHEDULE_PREFIX.encode()).hexdigest() != H1_PREFIX_SHA256:
        raise RuntimeError("H1_PREFIX_HASH_MISMATCH")
    df = pd.read_csv(io.StringIO(SCHEDULE_PREFIX), dtype=str)
    if list(df.columns) != ["date", "WIN", "WDO", "freeze_status"]:
        raise RuntimeError("H1_PREFIX_SCHEMA_MISMATCH")
    if not (df["freeze_status"] == "FROZEN_BEFORE_H1").all():
        raise RuntimeError("H1_PREFIX_FREEZE_STATUS_MISMATCH")
    return {
        str(r.date): {"WIN": str(r.WIN), "WDO": str(r.WDO)}
        for r in df.itertuples(index=False)
    }


def parse_ts(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, errors="raise")
    if getattr(ts.dt, "tz", None) is None:
        return ts.dt.tz_localize(TZ)
    return ts.dt.tz_convert(TZ)


def check_ohlc(df: pd.DataFrame, label: str) -> None:
    bad = ~(
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["high"])
    )
    if bad.any():
        raise RuntimeError(f"{label}_IMPOSSIBLE_OHLC rows={int(bad.sum())}")
    if (df["volume"] < 0).any():
        raise RuntimeError(f"{label}_NEGATIVE_VOLUME")


def check_tick_grid(df: pd.DataFrame, label: str) -> None:
    for root, tick in TICK.items():
        sub = df[df["root"] == root]
        if sub.empty:
            raise RuntimeError(f"{label}_{root}_MISSING")
        for col in ["open", "high", "low", "close"]:
            ratio = sub[col].astype(float).to_numpy() / tick
            ok = np.abs(ratio - np.round(ratio)) <= 1e-7 * np.maximum(1.0, np.abs(ratio))
            if not bool(ok.all()):
                raise RuntimeError(f"{label}_{root}_{col}_OFF_TICK rows={int((~ok).sum())}")


def recompute_m5(m1: pd.DataFrame) -> pd.DataFrame:
    x = m1.copy()
    x["timestamp"] = parse_ts(x["timestamp"])
    x = x.sort_values(["root", "symbol", "timestamp"], kind="mergesort")
    x["bucket"] = x["timestamp"].dt.floor("5min")
    return (
        x.groupby(["root", "symbol", "bucket"], as_index=False, sort=True)
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            trades=("trades", "sum"),
        )
        .rename(columns={"bucket": "timestamp"})
    )


def structural_qa(date: str, front: dict[str, str], m1: pd.DataFrame, m5: pd.DataFrame) -> dict:
    required = {"timestamp", "date", "root", "symbol", "open", "high", "low", "close", "volume", "trades"}
    for df, label in [(m1, "M1"), (m5, "M5")]:
        missing = required - set(df.columns)
        if missing:
            raise RuntimeError(f"{label}_SCHEMA_MISSING {sorted(missing)}")
        if df.duplicated(["root", "symbol", "timestamp"]).any():
            raise RuntimeError(f"{label}_DUPLICATE_KEYS")
        check_ohlc(df, label)
        check_tick_grid(df, label)

    expected = pd.date_range(
        start=pd.Timestamp(f"{date} 09:00", tz=TZ),
        periods=EXPECTED_M5,
        freq="5min",
    )
    coverage = {}
    lattice = {}
    contracts = {}
    for root in ["WIN", "WDO"]:
        sub = m5[m5["root"] == root].copy().sort_values("timestamp")
        syms = sorted(sub["symbol"].astype(str).unique().tolist())
        if syms != [front[root]]:
            raise RuntimeError(f"{root}_CONTRACT_MISMATCH got={syms} expected={[front[root]]}")
        contracts[root] = syms[0]
        coverage[root] = int(len(sub))
        if len(sub) != EXPECTED_M5:
            raise RuntimeError(f"{root}_M5_COUNT got={len(sub)} expected={EXPECTED_M5}")
        got = pd.DatetimeIndex(parse_ts(sub["timestamp"]))
        if not got.equals(expected):
            raise RuntimeError(
                f"{root}_M5_LATTICE_MISMATCH missing={len(expected.difference(got))} extra={len(got.difference(expected))}"
            )
        lattice[root] = {"start": str(got[0]), "end": str(got[-1]), "bars": int(len(got))}

    rec = recompute_m5(m1)
    off = m5.copy()
    off["timestamp"] = parse_ts(off["timestamp"])
    keys = ["root", "symbol", "timestamp"]
    a = rec.set_index(keys).sort_index()
    b = off.set_index(keys).sort_index()
    if not a.index.equals(b.index):
        raise RuntimeError(
            f"M1_TO_M5_INDEX_MISMATCH missing={len(b.index.difference(a.index))} extra={len(a.index.difference(b.index))}"
        )
    for col, tol in [
        ("open", 1e-9), ("high", 1e-9), ("low", 1e-9), ("close", 1e-9),
        ("volume", 1e-6), ("trades", 1e-9),
    ]:
        diff = (a[col].astype(float) - b[col].astype(float)).abs()
        if not bool((diff <= tol).all()):
            raise RuntimeError(f"M1_TO_M5_{col.upper()}_MISMATCH rows={int((diff > tol).sum())}")

    return {
        "contracts": contracts,
        "coverage_m5": coverage,
        "lattice_m5": lattice,
        "m1_rows": int(len(m1)),
        "m5_rows": int(len(m5)),
        "m1_to_m5_exact": True,
        "tick_grid": "PASS",
        "ohlc_integrity": "PASS",
        "timezone_normalization": TZ,
    }


def fetch_raw(date: str):
    url = URL.format(date=date)
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 B3 research v7 cloud structural-only", "Accept": "*/*"})
    last = None
    for attempt, delay in enumerate([0, 5, 15], start=1):
        if delay:
            time.sleep(delay)
        try:
            r = s.get(url, timeout=120)
            if r.status_code == 404:
                return None, {
                    "url": url, "http_status": 404, "attempt": attempt, "ok": False,
                    "state": "PENDING_SOURCE_NOT_PUBLISHED", "bytes": len(r.content),
                }
            if r.status_code != 200:
                last = f"HTTP_{r.status_code}"
                continue
            raw = bytes(r.content)
            if raw[:2] != b"PK":
                last = f"NON_ZIP_PREFIX_{raw[:16]!r}"
                continue
            return raw, {
                "url": url, "http_status": 200, "attempt": attempt, "ok": True,
                "state": "SOURCE_CAPTURED", "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        except Exception as exc:
            last = repr(exc)
    return None, {"url": url, "ok": False, "state": "SOURCE_RETRY_EXHAUSTED", "error": last}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--out-dir", default="artifacts/b3_h1_daily")
    ap.add_argument("--source-file", default=None)
    args = ap.parse_args()

    date = args.date or datetime.now(ZoneInfo(TZ)).date().isoformat()
    out = Path(args.out_dir) / date
    out.mkdir(parents=True, exist_ok=True)

    state = {
        "schema": "gate_btc.b3.h1.cloud_structural.v2",
        "date": date,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "economics_locked": True,
        "economic_functions_present": False,
        "economic_functions_called": False,
        "upstream_engine_sha256": UPSTREAM_ENGINE_SHA256,
        "full_frozen_schedule_sha256": FULL_FROZEN_SCHEDULE_SHA256,
        "h1_schedule_prefix_sha256": H1_PREFIX_SHA256,
        "blind_lock_sha256": BLIND_LOCK_SHA256,
        "timezone_qa_repair": "V7_TIMESTAMPS_AND_EXPECTED_LATTICE_NORMALIZED_TO_AMERICA_SAO_PAULO",
    }

    try:
        schedule = load_schedule()
        if date not in schedule:
            state.update(status="NO_FROZEN_H1_SCHEDULE_FOR_DATE", qualified=False, h1_increment_candidate=0)
            dump(out / "H1_STRUCTURAL_STATUS.json", state)
            print(json.dumps(state, indent=2, ensure_ascii=False))
            return 0

        front = schedule[date]
        state["front_contracts"] = front
        state["freeze_status"] = "FROZEN_BEFORE_H1"

        if args.source_file:
            raw = Path(args.source_file).read_bytes()
            source = {
                "source": "LOCAL_VALIDATION_OFFICIAL_RAW", "ok": raw[:2] == b"PK",
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            }
        else:
            raw, source = fetch_raw(date)
        state["source"] = source

        if raw is None:
            state.update(status=source.get("state", "SOURCE_UNAVAILABLE"), qualified=False, h1_increment_candidate=0)
            dump(out / "H1_STRUCTURAL_STATUS.json", state)
            print(json.dumps(state, indent=2, ensure_ascii=False))
            return 0

        (out / f"{date}_NEGOCIOSAVISTA_original.zip").write_bytes(raw)
        m1, m5, stats, member = process_zip(raw, date, front)
        m1.to_csv(out / "M1.csv.gz", index=False, compression="gzip")
        m5.to_csv(out / "M5.csv.gz", index=False, compression="gzip")
        qa = structural_qa(date, front, m1, m5)

        state.update(
            status="STRUCTURAL_PASS", qualified=True, h1_increment_candidate=1,
            source_member=member, engine_stats=stats, qa=qa,
        )
        dump(out / "H1_STRUCTURAL_STATUS.json", state)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        state.update(
            status="STRUCTURAL_FAIL_CLOSED", qualified=False, h1_increment_candidate=0,
            error=repr(exc),
        )
        dump(out / "H1_STRUCTURAL_STATUS.json", state)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
