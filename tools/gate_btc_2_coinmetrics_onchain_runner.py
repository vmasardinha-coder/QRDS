#!/usr/bin/env python3
"""External BTSE standalone: Coin Metrics BTC active-address risk gate.

Historical research only. Today's Community API response is not treated as a
revision-versioned PIT dataset, even if the frozen historical hypothesis passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

BASE_URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
START = "2020-01-01"
END = "2026-09-20"
COST = 0.001


def fetch_bytes(params: dict[str, str], retries: int = 3) -> bytes:
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - live CI
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Coin Metrics Community API request failed: {last}")


def parse_rows(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict) or not isinstance(obj.get("data"), list):
        raise ValueError("unexpected Coin Metrics response")
    if obj.get("next_page_token"):
        raise ValueError("unexpected pagination: preregistered page_size should cover requested window")
    rows = []
    for item in obj["data"]:
        if not isinstance(item, dict) or item.get("asset") != "btc":
            continue
        try:
            day = datetime.fromisoformat(str(item["time"]).replace("Z", "+00:00")).date()
            adr = float(item["AdrActCnt"])
            price = float(item["PriceUSD"])
        except (KeyError, TypeError, ValueError):
            continue
        if adr <= 0 or price <= 0 or not (math.isfinite(adr) and math.isfinite(price)):
            continue
        rows.append({"day": day, "adr": adr, "price": price})
    rows.sort(key=lambda r: r["day"])
    return rows


def build_observations(rows: list[dict]) -> tuple[list[dict], dict]:
    by_day = {r["day"]: r for r in rows}
    duplicate_rows = len(rows) - len(by_day)
    days = sorted(by_day)
    monotonic = all(days[i] < days[i + 1] for i in range(len(days) - 1))
    obs = []
    for d in days:
        d7 = date.fromordinal(d.toordinal() - 7)
        d1 = date.fromordinal(d.toordinal() + 1)
        d2 = date.fromordinal(d.toordinal() + 2)
        if d7 not in by_day or d1 not in by_day or d2 not in by_day:
            continue
        state = 1 if by_day[d]["adr"] > by_day[d7]["adr"] else 0
        gross = by_day[d2]["price"] / by_day[d1]["price"]
        if gross <= 0 or not math.isfinite(gross):
            continue
        obs.append({
            "feature_day": d.isoformat(),
            "target_start_day": d1.isoformat(),
            "target_end_day": d2.isoformat(),
            "adr_now": by_day[d]["adr"],
            "adr_7d_ago": by_day[d7]["adr"],
            "state_long": state,
            "price_start": by_day[d1]["price"],
            "price_end": by_day[d2]["price"],
            "gross_return": gross,
        })
    details = {
        "valid_source_rows": len(rows),
        "duplicate_timestamps": duplicate_rows,
        "strictly_increasing": monotonic,
        "causal_observations": len(obs),
        "long_observations": sum(o["state_long"] for o in obs),
        "flat_observations": sum(1 - o["state_long"] for o in obs),
    }
    return obs, details


def max_drawdown(path: list[float]) -> float:
    peak = path[0]
    worst = 0.0
    for x in path:
        peak = max(peak, x)
        worst = min(worst, x / peak - 1.0)
    return worst


def ann_stats(equity_path: list[float], period_returns: list[float], n: int) -> tuple[float, float, float]:
    ann_ret = (equity_path[-1] / equity_path[0]) ** (365.0 / max(1, n)) - 1.0
    if len(period_returns) > 1:
        vol = statistics.stdev(period_returns) * math.sqrt(365.0)
    else:
        vol = 0.0
    sharpe = ann_ret / vol if vol > 0 else 0.0
    return ann_ret, vol, sharpe


def replay(obs: list[dict], initial: float = 10000.0, cost: float = COST) -> dict:
    strategy = initial
    strat_path = [strategy]
    strat_period_returns = []
    prev_state = 0
    transitions = 0
    for o in obs:
        state = int(o["state_long"])
        before = strategy
        if state != prev_state:
            strategy *= 1.0 - cost
            transitions += 1
        if state:
            strategy *= o["gross_return"]
        strat_period_returns.append(strategy / before - 1.0)
        strat_path.append(strategy)
        prev_state = state
    if prev_state == 1:
        before = strategy
        strategy *= 1.0 - cost
        transitions += 1
        strat_path[-1] = strategy
        if strat_period_returns:
            strat_period_returns[-1] = strategy / strat_path[-2] - 1.0

    baseline = initial * (1.0 - cost)
    base_path = [initial, baseline]
    base_period_returns = []
    for o in obs:
        before = baseline
        baseline *= o["gross_return"]
        base_period_returns.append(baseline / before - 1.0)
        base_path.append(baseline)
    baseline *= 1.0 - cost
    base_path[-1] = baseline
    if base_period_returns:
        base_period_returns[-1] = baseline / base_path[-2] - 1.0

    s_ann, s_vol, s_sh = ann_stats(strat_path, strat_period_returns, len(obs))
    b_ann, b_vol, b_sh = ann_stats(base_path, base_period_returns, len(obs))
    s_dd = max_drawdown(strat_path)
    b_dd = max_drawdown(base_path)
    dd_improvement_pp = (s_dd - b_dd) * 100.0
    equity_ratio = strategy / baseline if baseline > 0 else 0.0
    return {
        "strategy_final_equity": strategy,
        "baseline_final_equity": baseline,
        "strategy_total_return": strategy / initial - 1.0,
        "baseline_total_return": baseline / initial - 1.0,
        "strategy_max_drawdown": s_dd,
        "baseline_max_drawdown": b_dd,
        "drawdown_improvement_pp": dd_improvement_pp,
        "strategy_to_baseline_final_equity_ratio": equity_ratio,
        "state_transitions_including_final_exit": transitions,
        "strategy_annualized_return": s_ann,
        "baseline_annualized_return": b_ann,
        "strategy_annualized_volatility": s_vol,
        "baseline_annualized_volatility": b_vol,
        "strategy_sharpe_like": s_sh,
        "baseline_sharpe_like": b_sh,
        "feature_pass": dd_improvement_pp >= 5.0 and equity_ratio >= 0.90,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    params = {
        "assets": "btc",
        "metrics": "AdrActCnt,PriceUSD",
        "frequency": "1d",
        "start_time": START,
        "end_time": END,
        "page_size": "10000",
    }
    raw = fetch_bytes(params)
    (out / "RAW.json").write_bytes(raw)
    raw_sha = hashlib.sha256(raw).hexdigest()
    rows = parse_rows(raw)
    obs, data = build_observations(rows)
    transitions_pre = sum(
        1 for i, o in enumerate(obs)
        if int(o["state_long"]) != (int(obs[i-1]["state_long"]) if i else 0)
    )
    data_gate = bool(
        data["valid_source_rows"] >= 1500
        and data["causal_observations"] >= 1400
        and data["duplicate_timestamps"] == 0
        and data["strictly_increasing"]
        and data["long_observations"] > 0
        and data["flat_observations"] > 0
        and transitions_pre >= 20
    )
    result = replay(obs) if data_gate else None
    if not data_gate:
        disposition = "DATA_CAPABILITY_NOT_ESTABLISHED"
    elif result and result["feature_pass"]:
        disposition = "HISTORICAL_CANDIDATE / PROSPECTIVE_PIT_VALIDATION_REQUIRED"
    else:
        disposition = "FEATURE_REJECTED / SOURCE_RETAINED_AS_RESEARCH_COMPONENT"

    with (out / "OBSERVATIONS.jsonl").open("w", encoding="utf-8") as f:
        for o in obs:
            f.write(json.dumps(o, sort_keys=True) + "\n")
    summary = {
        "schema_version": "GATE_BTC_2_COINMETRICS_ONCHAIN_V1",
        "provider": "Coin Metrics Community API v4",
        "asset": "btc",
        "metrics": ["AdrActCnt", "PriceUSD"],
        "requested_start": START,
        "requested_end": END,
        "raw_sha256": raw_sha,
        **data,
        "state_transitions_before_final_exit": transitions_pre,
        "data_gate_pass": data_gate,
        **(result or {}),
        "disposition": disposition,
        "historical_response_is_revision_versioned_pit_proven": False,
        "prospective_pit_validation_required": True,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "factory_runtime_untouched": True,
        "economic_claim_authorized": False,
        "factory_migration_authorized": False,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if data_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
