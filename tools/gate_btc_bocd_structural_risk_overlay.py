#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import requests

from bocd import Detector
from bocd.hazards import ConstantHazard
from bocd.models import StudentTModel

UPSTREAM_SHA = "0c09315e9102ddea885bb7164e47b61a95e99dac"
INST_ID = "BTC-USDT"
BAR = "1H"
N_BARS = 8000
HAZARD_RATE = 1 / 720
MAX_RUN_LENGTH = 2000
RESET_THRESHOLD = 20
COOLDOWN_HOURS = 24
COST_PER_POSITION_CHANGE = 0.001
INITIAL_EQUITY = 10000.0
OUTDIR = Path("bocd_evidence")


def fetch_okx_history() -> list[dict]:
    url = "https://www.okx.com/api/v5/market/history-candles"
    rows: dict[int, dict] = {}
    after = None
    session = requests.Session()
    while len(rows) < N_BARS:
        params = {"instId": INST_ID, "bar": BAR, "limit": "100"}
        if after is not None:
            params["after"] = str(after)
        last_exc = None
        for attempt in range(6):
            try:
                r = session.get(url, params=params, timeout=30)
                if r.status_code == 429:
                    time.sleep(1.0 + attempt)
                    continue
                r.raise_for_status()
                payload = r.json()
                if payload.get("code") != "0":
                    raise RuntimeError(payload)
                batch = payload.get("data", [])
                break
            except Exception as exc:
                last_exc = exc
                time.sleep(0.5 * (attempt + 1))
        else:
            raise RuntimeError(f"OKX fetch failed: {last_exc}")
        if not batch:
            break
        min_ts = None
        for x in batch:
            if len(x) < 9 or x[8] != "1":
                continue
            ts = int(x[0])
            rows[ts] = {
                "ts": ts,
                "open": float(x[1]),
                "high": float(x[2]),
                "low": float(x[3]),
                "close": float(x[4]),
                "volume": float(x[5]),
            }
            min_ts = ts if min_ts is None else min(min_ts, ts)
        if min_ts is None:
            break
        after = min_ts
        time.sleep(0.06)
    ordered = [rows[k] for k in sorted(rows)]
    if len(ordered) < N_BARS:
        raise RuntimeError(f"requested {N_BARS} closed bars, got {len(ordered)}")
    return ordered[-N_BARS:]


def detector() -> Detector:
    return Detector(
        model=StudentTModel(),
        hazard=ConstantHazard(rate=HAZARD_RATE),
        max_run_length=MAX_RUN_LENGTH,
    )


def detect_stream(observations: np.ndarray) -> list[int]:
    d = detector()
    prev_rl = 0
    events: list[int] = []
    for i, x in enumerate(observations):
        result = d.update(float(x))
        rl = int(result.most_likely_run_length)
        if prev_rl - rl > RESET_THRESHOLD:
            events.append(i)
        prev_rl = rl
    return events


def synthetic_sanity() -> dict:
    rng = np.random.default_rng(20260921)
    x = np.concatenate([
        rng.normal(0, 0.2, 500),
        rng.normal(0, 2.0, 500),
        rng.normal(0, 0.3, 500),
    ])
    obs = np.abs(x)
    events = detect_stream(obs)
    planted = [500, 1000]
    matched = [p for p in planted if any(abs(e - p) <= 100 for e in events)]
    return {
        "n": int(len(obs)),
        "planted_breaks": planted,
        "detected_events": events,
        "matched_planted_breaks": matched,
        "pass": bool(matched),
    }


def max_drawdown(path: list[float]) -> float:
    peak = path[0]
    mdd = 0.0
    for v in path:
        peak = max(peak, v)
        dd = v / peak - 1.0
        mdd = min(mdd, dd)
    return mdd


def backtest(returns: np.ndarray, positions: np.ndarray) -> dict:
    eq = INITIAL_EQUITY
    path = [eq]
    prev_pos = 0.0
    changes = 0
    for r, pos in zip(returns, positions):
        if pos != prev_pos:
            eq *= 1.0 - COST_PER_POSITION_CHANGE
            changes += 1
        eq *= 1.0 + pos * float(r)
        path.append(eq)
        prev_pos = pos
    if prev_pos != 0.0:
        eq *= 1.0 - COST_PER_POSITION_CHANGE
        changes += 1
        path.append(eq)
    return {
        "initial_equity": INITIAL_EQUITY,
        "final_equity": eq,
        "net_return": eq / INITIAL_EQUITY - 1.0,
        "max_drawdown": max_drawdown(path),
        "position_changes": changes,
        "round_trip_equivalent": changes / 2.0,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    bars = fetch_okx_history()
    rows_blob = "\n".join(json.dumps(x, sort_keys=True, separators=(",", ":")) for x in bars).encode()
    rows_sha = hashlib.sha256(rows_blob).hexdigest()

    closes = np.array([x["close"] for x in bars], dtype=float)
    logret = np.diff(np.log(closes))
    simple_ret = closes[1:] / closes[:-1] - 1.0
    observations = np.abs(logret) * 100.0

    events_obs = detect_stream(observations[:-1])
    n_decisions = len(observations) - 1
    next_returns = simple_ret[1:]
    assert len(next_returns) == n_decisions

    baseline_pos = np.ones(n_decisions, dtype=float)
    overlay_pos = np.ones(n_decisions, dtype=float)
    event_set = set(events_obs)
    cooldown = 0
    for i in range(n_decisions):
        if i in event_set:
            cooldown = COOLDOWN_HOURS
        if cooldown > 0:
            overlay_pos[i] = 0.0
            cooldown -= 1

    baseline = backtest(next_returns, baseline_pos)
    overlay = backtest(next_returns, overlay_pos)

    abs_next = np.abs(next_returns)
    rolling24 = []
    for i in range(0, len(abs_next) - COOLDOWN_HOURS + 1):
        rolling24.append(float(np.mean(abs_next[i:i + COOLDOWN_HOURS])))
    unconditional = float(np.mean(rolling24)) if rolling24 else float("nan")
    event_windows = [
        float(np.mean(abs_next[e:e + COOLDOWN_HOURS]))
        for e in events_obs
        if e + COOLDOWN_HOURS <= len(abs_next)
    ]
    event_mean = float(np.mean(event_windows)) if event_windows else float("nan")
    enrichment = event_mean / unconditional if unconditional > 0 and math.isfinite(event_mean) else float("nan")

    event_count = len(events_obs)
    dd_base = abs(float(baseline["max_drawdown"]))
    dd_overlay = abs(float(overlay["max_drawdown"]))
    dd_improvement = (dd_base - dd_overlay) / dd_base if dd_base > 0 else 0.0
    equity_ratio = float(overlay["final_equity"]) / float(baseline["final_equity"])

    gates = {
        "event_count_3_to_100": 3 <= event_count <= 100,
        "volatility_enrichment_ge_1_25": bool(math.isfinite(enrichment) and enrichment >= 1.25),
        "max_drawdown_relative_improvement_ge_10pct": dd_improvement >= 0.10,
        "final_equity_ratio_ge_0_98": equity_ratio >= 0.98,
    }
    synth = synthetic_sanity()
    real_market_pass = all(gates.values())
    overall_pass = bool(synth["pass"] and real_market_pass)

    out = {
        "schema": "gate_btc.external_bocd_structural_risk_overlay.v1",
        "research_only": True,
        "shadow_only": True,
        "real_capital_used": 0,
        "upstream": "fiannai/bocd",
        "upstream_sha": UPSTREAM_SHA,
        "market": INST_ID,
        "bar": BAR,
        "rows": len(bars),
        "rows_sha256": rows_sha,
        "first_ts_ms": bars[0]["ts"],
        "last_ts_ms": bars[-1]["ts"],
        "hazard_rate": HAZARD_RATE,
        "max_run_length": MAX_RUN_LENGTH,
        "reset_threshold": RESET_THRESHOLD,
        "cooldown_hours": COOLDOWN_HOURS,
        "cost_per_position_change": COST_PER_POSITION_CHANGE,
        "synthetic_sanity": synth,
        "real_market": {
            "resolved_decisions": n_decisions,
            "event_count": event_count,
            "event_indices": events_obs,
            "unconditional_mean_abs_hourly_return_in_24h_windows": unconditional,
            "event_mean_abs_hourly_return_next_24h": event_mean,
            "volatility_enrichment_ratio": enrichment,
            "baseline": baseline,
            "overlay": overlay,
            "max_drawdown_relative_improvement": dd_improvement,
            "final_equity_ratio": equity_ratio,
            "gates": gates,
            "pass": real_market_pass,
        },
        "pass": overall_pass,
        "disposition": "PASS" if overall_pass else "REJECT_FROZEN_CONFIGURATION",
    }
    (OUTDIR / "RESULT.json").write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    (OUTDIR / "ROWS_SHA256.txt").write_text(rows_sha + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
