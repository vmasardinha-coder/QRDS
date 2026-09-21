import hashlib
import json
import math
import time
from datetime import datetime, timezone

import ccxt
from river import compose, drift, linear_model, preprocessing

SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
TARGET_BARS = 8000
START_CASH = 10_000.0
COST_PER_SIDE = 0.001
MAX_LAG = 24
UPSTREAM_COMMIT = "64285b9dd6c606804753235fe992bcf25b9856ee"


def fetch_rows():
    ex = ccxt.okx({"enableRateLimit": True})
    since = ex.milliseconds() - (TARGET_BARS + 100) * 3_600_000
    rows = []
    while len(rows) < TARGET_BARS:
        batch = ex.fetch_ohlcv(
            SYMBOL,
            TIMEFRAME,
            since=since,
            limit=min(300, TARGET_BARS - len(rows)),
        )
        if not batch:
            break
        if rows:
            batch = [r for r in batch if r[0] > rows[-1][0]]
        if not batch:
            break
        rows.extend(batch)
        since = rows[-1][0] + 1
        time.sleep(ex.rateLimit / 1000)
    rows = rows[-TARGET_BARS:]
    if len(rows) < 1000:
        raise RuntimeError(f"insufficient rows: {len(rows)}")
    return rows


def pct(a, b):
    return a / b - 1.0


def make_features(rows, t):
    closes = [float(rows[i][4]) for i in range(t - MAX_LAG, t + 1)]
    one_hour = [pct(closes[i], closes[i - 1]) for i in range(1, len(closes))]
    mean = sum(one_hour) / len(one_hour)
    variance = sum((r - mean) ** 2 for r in one_hour) / len(one_hour)
    current = rows[t]
    close_t = float(current[4])
    return {
        "ret_1h": pct(close_t, float(rows[t - 1][4])),
        "ret_3h": pct(close_t, float(rows[t - 3][4])),
        "ret_6h": pct(close_t, float(rows[t - 6][4])),
        "ret_12h": pct(close_t, float(rows[t - 12][4])),
        "ret_24h": pct(close_t, float(rows[t - 24][4])),
        "rv_24h": math.sqrt(variance),
        "intrabar_close_open": pct(close_t, float(current[1])),
        "range_norm": (float(current[2]) - float(current[3])) / close_t,
    }


def make_model():
    return compose.Pipeline(
        preprocessing.StandardScaler(),
        linear_model.LinearRegression(),
    )


def max_drawdown(curve):
    peak = curve[0]
    mdd = 0.0
    for value in curve:
        peak = max(peak, value)
        mdd = min(mdd, value / peak - 1.0)
    return mdd


def arm_state(with_drift):
    return {
        "model": make_model(),
        "detector": drift.ADWIN() if with_drift else None,
        "predictions": [],
        "targets": [],
        "equity": START_CASH,
        "curve": [START_CASH],
        "trades": 0,
        "drifts": [],
    }


def step_arm(state, x, y, entry_open, exit_open, resolved_ts, with_drift):
    pred = state["model"].predict_one(x)
    if pred is None:
        pred = 0.0
    pred = float(pred)

    if pred > 0.0:
        gross_multiplier = exit_open / entry_open
        net_multiplier = gross_multiplier * (1.0 - COST_PER_SIDE) / (1.0 + COST_PER_SIDE)
        state["equity"] *= net_multiplier
        state["trades"] += 1
    state["curve"].append(state["equity"])
    state["predictions"].append(pred)
    state["targets"].append(y)

    err = abs(pred - y)
    if with_drift:
        state["detector"].update(err)
        if state["detector"].drift_detected:
            state["drifts"].append(resolved_ts)
            state["model"] = make_model()
            state["detector"] = drift.ADWIN()
            state["model"].learn_one(x, y)
            return
    state["model"].learn_one(x, y)


def summarize(state):
    preds = state["predictions"]
    ys = state["targets"]
    n = len(ys)
    mae = sum(abs(p - y) for p, y in zip(preds, ys)) / n
    rmse = math.sqrt(sum((p - y) ** 2 for p, y in zip(preds, ys)) / n)
    directional = sum((p > 0) == (y > 0) for p, y in zip(preds, ys)) / n
    return {
        "samples": n,
        "mae": mae,
        "rmse": rmse,
        "directional_accuracy": directional,
        "final_equity": state["equity"],
        "net_return": state["equity"] / START_CASH - 1.0,
        "max_drawdown": max_drawdown(state["curve"]),
        "round_trip_trades": state["trades"],
        "drift_count": len(state["drifts"]),
        "drift_timestamps": state["drifts"],
    }


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def main():
    rows = fetch_rows()
    rows_blob = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()
    rows_sha = hashlib.sha256(rows_blob).hexdigest()

    baseline = arm_state(False)
    reset = arm_state(True)

    for t in range(MAX_LAG, len(rows) - 2):
        x = make_features(rows, t)
        entry_open = float(rows[t + 1][1])
        exit_open = float(rows[t + 2][1])
        y = exit_open / entry_open - 1.0
        resolved_ts = iso(rows[t + 2][0])
        step_arm(baseline, x, y, entry_open, exit_open, resolved_ts, False)
        step_arm(reset, x, y, entry_open, exit_open, resolved_ts, True)

    b = summarize(baseline)
    d = summarize(reset)
    primary = {
        "lower_mae": d["mae"] < b["mae"],
        "higher_net_final_equity": d["final_equity"] > b["final_equity"],
    }
    primary["pass"] = all(primary.values())

    report = {
        "source_system": "River",
        "release": "0.26.1",
        "upstream_commit": UPSTREAM_COMMIT,
        "research_only": True,
        "shadow_only": True,
        "real_capital": 0,
        "hypothesis": "online_error_drift_reset",
        "data": {
            "venue": "OKX",
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "bars": len(rows),
            "start": iso(rows[0][0]),
            "end": iso(rows[-1][0]),
            "rows_sha256": rows_sha,
        },
        "frozen": {
            "learner": "StandardScaler -> LinearRegression",
            "drift_detector": "ADWIN defaults",
            "target": "open[t+1] to open[t+2] return predicted after close[t]",
            "cost_per_side": COST_PER_SIDE,
            "start_cash": START_CASH,
            "features": [
                "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
                "rv_24h", "intrabar_close_open", "range_norm",
            ],
        },
        "baseline_no_reset": b,
        "adwin_drift_reset": d,
        "deltas": {
            "mae": d["mae"] - b["mae"],
            "rmse": d["rmse"] - b["rmse"],
            "directional_accuracy_pp": (d["directional_accuracy"] - b["directional_accuracy"]) * 100.0,
            "net_return_pp": (d["net_return"] - b["net_return"]) * 100.0,
            "max_drawdown_pp": (d["max_drawdown"] - b["max_drawdown"]) * 100.0,
        },
        "primary_rule": primary,
        "factory_migration_authorized": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
