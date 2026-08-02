#!/usr/bin/env python3
"""QOS V2A integrity build used by QOS Master v1.3.

Public-data, research-only portfolio study.  The historical engine applies a
signal only after the signal bar has closed.  Current-month signals are kept
separate from completed-month backtests.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qos_matplotlib")

try:
    import requests
except Exception:  # offline contract tests
    requests = None

try:
    from tqdm import tqdm
except Exception:  # offline contract tests
    def tqdm(values, *args, **kwargs):
        return values

try:
    import matplotlib.pyplot as plt
except Exception:  # charts are optional, evidence files are not
    plt = None


VERSION = "QOS_V2A_INTEGRITY_0.4"
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
CFG = json.loads((ROOT / "config_v2a.json").read_text(encoding="utf-8"))
START_DATE = pd.Timestamp(CFG["start_date"])
INITIAL = float(CFG["initial_brl"])

STABLES = set(CFG.get("stable_symbols", [])) | {
    "USDT", "USDC", "DAI", "TUSD", "FDUSD", "USDE", "USDG", "BUSD",
    "PYUSD", "USDD", "FRAX", "USDS", "USDP", "GUSD", "EURC", "RLUSD",
    "USDL", "USDF", "USD0", "USDTB", "BFUSD", "UST", "USTC",
}
CORE = {"BTC", "ETH"}
BLACKLIST = {"LUNC", "FTT", "UST", "USTC"}
AMBIGUOUS = {"LIT", "XAR", "VVV", "STABLE", "FIGR_HELOC", "WBT", "RAIN", "CC", "H", "UB", "BILL", "LAB"}
HIGH_NOISE = {"FARTCOIN", "TRUMP", "PI"}
VICTOR_PROXY = {"BTC": 0.19, "ETH": 0.12, "BNB": 0.07, "SOL": 0.05, "SUI": 0.14, "ASTER": 0.02, "CASH": 0.41}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def standard_ticker(value: object) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{2,12}", str(value or "").strip().upper()))


def reset_run_dirs() -> None:
    for directory in (DATA_RAW, DATA_PROCESSED, OUT):
        directory.mkdir(parents=True, exist_ok=True)
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def save_df(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"saved {path} rows={len(df):,}", flush=True)


def save_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(temporary, path)


def session_or_raise():
    if requests is None:
        raise RuntimeError("requests is required outside fixture mode")
    session = requests.Session()
    session.headers.update({"User-Agent": "QOS-V2A-Integrity/0.3"})
    return session


def fetch_coingecko_universe(session, top_n: int) -> pd.DataFrame:
    rows = []
    for page in range(1, math.ceil(top_n / 250) + 1):
        response = session.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd", "order": "market_cap_desc", "per_page": 250,
                "page": page, "sparkline": "false", "price_change_percentage": "24h,7d,30d",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"CoinGecko universe failed: HTTP {response.status_code}")
        rows.extend(response.json())
        time.sleep(1.2)
    frame = pd.DataFrame(rows).head(top_n)
    if frame.empty:
        raise RuntimeError("CoinGecko returned an empty universe")
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame["standard_ticker"] = frame["symbol"].map(standard_ticker)
    frame["is_stable"] = frame["symbol"].isin(STABLES)
    frame["is_blocked"] = frame["symbol"].isin(BLACKLIST | AMBIGUOUS)
    save_df(frame, DATA_RAW / "coingecko_current_universe_v04.csv")
    return frame


def parse_cdd_csv(text: str, symbol: str) -> pd.DataFrame:
    from io import StringIO

    lines = text.splitlines()
    header_index = next((i for i, line in enumerate(lines[:8]) if "date" in line.lower() and "close" in line.lower()), None)
    if header_index is None:
        raise ValueError("CryptoDataDownload header not found")
    frame = pd.read_csv(StringIO("\n".join(lines[header_index:])))
    frame.columns = [c.strip().lower().replace(" ", "_") for c in frame.columns]
    if "date" not in frame or "close" not in frame:
        raise ValueError("CryptoDataDownload columns missing")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    frame["close_usd"] = pd.to_numeric(frame["close"], errors="coerce")
    volume_column = next((c for c in ("volume_usdt", "volume_usd", "volume_usdc", "volume") if c in frame), None)
    frame["volume_usd"] = pd.to_numeric(frame[volume_column], errors="coerce") if volume_column else np.nan
    frame["symbol"] = symbol
    frame["source"] = "cdd"
    return frame[["date", "symbol", "close_usd", "volume_usd", "source"]].dropna(subset=["date", "close_usd"]).sort_values("date")


def fetch_cdd_symbol(session, symbol: str) -> pd.DataFrame:
    response = session.get(f"https://www.cryptodatadownload.com/cdd/Binance_{symbol}USDT_d.csv", timeout=40)
    if response.status_code != 200:
        raise RuntimeError(f"CDD unavailable: HTTP {response.status_code}")
    return parse_cdd_csv(response.text, symbol)


def fetch_binance_klines(session, symbol: str) -> pd.DataFrame:
    start_ms = int(START_DATE.timestamp() * 1000)
    rows = []
    while True:
        response = session.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol + "USDT", "interval": "1d", "startTime": start_ms, "limit": 1000},
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Binance kline failed: HTTP {response.status_code}")
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        start_ms = int(batch[-1][0]) + 86_400_000
        if len(batch) < 1000:
            break
        time.sleep(0.15)
    if not rows:
        raise RuntimeError("Binance returned no candles")
    columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "n_trades", "taker_base", "taker_quote", "ignore"]
    frame = pd.DataFrame(rows, columns=columns)
    frame["date"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["symbol"] = symbol
    frame["close_usd"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume_usd"] = pd.to_numeric(frame["quote_volume"], errors="coerce")
    frame["source"] = "binance"
    return frame[["date", "symbol", "close_usd", "volume_usd", "source"]]


def fetch_okx_candles(session, symbol: str) -> pd.DataFrame:
    rows = []
    cursor = None
    for _ in range(14):
        params = {"instId": f"{symbol}-USDT", "bar": "1D", "limit": "300"}
        if cursor:
            params["after"] = cursor
        response = session.get("https://www.okx.com/api/v5/market/history-candles", params=params, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"OKX candles failed: HTTP {response.status_code}")
        batch = response.json().get("data", [])
        if not batch:
            break
        rows.extend(batch)
        next_cursor = str(batch[-1][0])
        if next_cursor == cursor or len(batch) < 300:
            break
        cursor = next_cursor
        time.sleep(0.15)
    if not rows:
        raise RuntimeError("OKX returned no candles")
    frame = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "vol_ccy", "vol_quote", "confirm"])
    frame["date"] = pd.to_datetime(pd.to_numeric(frame["ts"]), unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["symbol"] = symbol
    frame["close_usd"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume_usd"] = pd.to_numeric(frame["vol_quote"], errors="coerce")
    frame["source"] = "okx"
    return frame[["date", "symbol", "close_usd", "volume_usd", "source"]].drop_duplicates(["date", "symbol"]).sort_values("date")


def fetch_candles_for_universe(session, universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = universe[
        universe["standard_ticker"]
        & ~universe["is_stable"]
        & ~universe["is_blocked"]
    ].head(int(CFG["max_assets_to_fetch"]))
    symbols = list(dict.fromkeys(["BTC", "ETH"] + candidates["symbol"].tolist()))
    histories, failures = [], []
    for symbol in tqdm(symbols, desc="public candles"):
        last_error = "not_attempted"
        selected = None
        for name, loader in (("cdd", fetch_cdd_symbol), ("binance", fetch_binance_klines), ("okx", fetch_okx_candles)):
            try:
                candidate = loader(session, symbol)
                if len(candidate) >= 200:
                    selected = candidate
                    break
                last_error = f"{name}: only {len(candidate)} rows"
            except Exception as exc:
                last_error = f"{name}: {type(exc).__name__}: {str(exc)[:160]}"
        if selected is None:
            failures.append({"symbol": symbol, "reason": last_error})
        else:
            histories.append(selected)
        time.sleep(0.08)
    master = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd", "source"])
    if not master.empty:
        master["date"] = pd.to_datetime(master["date"]).dt.tz_localize(None).dt.normalize()
        master = master[master["date"] >= START_DATE].drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
    failure_frame = pd.DataFrame(failures, columns=["symbol", "reason"])
    save_df(failure_frame, OUT / "download_failures_v2a.csv")
    save_df(master, DATA_PROCESSED / "qos_v2a_master_daily.csv")
    return master, failure_frame


def build_fixture_master(end_date: str = "2026-07-16") -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", end_date, freq="D")
    symbols = ["BTC", "ETH", "SOL", "BNB", "SUI", "AAVE", "LINK", "INJ", "NEAR", "ZEC", "JUP", "MORPHO"]
    rng = np.random.default_rng(3003)
    rows = []
    for index, symbol in enumerate(symbols):
        drift = 0.00025 + index * 0.000015
        volatility = 0.018 + (index % 5) * 0.003
        returns = drift + volatility * rng.standard_normal(len(dates)) + 0.002 * np.sin(np.arange(len(dates)) / (13 + index))
        prices = (100 + index * 7) * np.exp(np.cumsum(returns))
        volumes = (20_000_000 + index * 1_000_000) * (1 + 0.1 * np.sin(np.arange(len(dates)) / 17))
        rows.extend({"date": date, "symbol": symbol, "close_usd": price, "volume_usd": volume, "source": "fixture"} for date, price, volume in zip(dates, prices, volumes))
    frame = pd.DataFrame(rows).sort_values(["symbol", "date"])
    save_df(frame, DATA_PROCESSED / "qos_v2a_master_daily.csv")
    save_df(pd.DataFrame(columns=["symbol", "reason"]), OUT / "download_failures_v2a.csv")
    return frame


def zscore_cross(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    std = numeric.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return pd.Series(0.0, index=series.index)
    return (numeric - numeric.mean()) / std


def _feature_snapshot(close: pd.DataFrame, volume: pd.DataFrame, signal_date: pd.Timestamp) -> pd.DataFrame:
    price_window = close.loc[:signal_date].tail(220)
    volume_window = volume.loc[:signal_date].tail(220)
    if len(price_window) < 181:
        return pd.DataFrame()
    last = price_window.iloc[-1]
    m90 = last / price_window.iloc[-91] - 1
    m180 = last / price_window.iloc[-181] - 1
    vol90 = price_window.pct_change().tail(90).std() * np.sqrt(365)
    risk_adj = m90 / vol90.replace(0, np.nan)
    volume_now = volume_window.tail(30).mean()
    volume_previous = volume_window.iloc[-90:-60].mean()
    volume_growth = volume_now / volume_previous.replace(0, np.nan) - 1
    liquidity = np.log1p(volume_now)
    btc_m90 = np.nan
    if "BTC" in price_window and price_window["BTC"].dropna().shape[0] >= 91:
        btc_series = price_window["BTC"].dropna()
        btc_m90 = btc_series.iloc[-1] / btc_series.iloc[-91] - 1
    relative = m90 - btc_m90
    last_valid = close.loc[:signal_date].apply(lambda s: s.last_valid_index())
    frame = pd.DataFrame({
        "symbol": last.index, "signal_date": signal_date, "mom90": m90.values,
        "mom180": m180.values, "relbtc90": relative.values, "risk_adj": risk_adj.values,
        "vol_growth": volume_growth.values, "liquidity": liquidity.values,
        "last_observation_date": [last_valid.get(s) for s in last.index],
    })
    frame["staleness_days"] = (signal_date - pd.to_datetime(frame["last_observation_date"])).dt.days
    frame = frame.dropna(subset=["mom90", "mom180", "relbtc90", "risk_adj"])
    frame = frame[frame["staleness_days"].fillna(999) <= 5].copy()
    for column in ("mom90", "mom180", "relbtc90", "risk_adj", "vol_growth", "liquidity"):
        clean = frame[column].replace([np.inf, -np.inf], np.nan)
        frame[column + "_z"] = zscore_cross(clean.fillna(clean.median()))
    weights = CFG["score_weights"]
    frame["score"] = sum(float(weights[key]) * frame[key + "_z"] for key in weights)
    frame["is_core"] = frame["symbol"].isin(CORE)
    frame["is_stable"] = frame["symbol"].isin(STABLES)
    frame["is_blocked"] = frame["symbol"].isin(BLACKLIST | AMBIGUOUS | HIGH_NOISE) | ~frame["symbol"].map(standard_ticker)
    regime = "UNKNOWN"
    if "BTC" in price_window and price_window["BTC"].dropna().shape[0] >= 200:
        btc = price_window["BTC"].dropna()
        regime = "RISK_ON" if btc.iloc[-1] > btc.tail(200).mean() and btc.iloc[-1] / btc.iloc[-91] - 1 > 0 else "DEFENSIVE"
    frame["btc_regime"] = regime
    frame["data_as_of"] = signal_date
    return frame


def compute_monthly_features(master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    frame = master.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None).dt.normalize()
    close = frame.pivot(index="date", columns="symbol", values="close_usd").sort_index().ffill(limit=5)
    volume = frame.pivot(index="date", columns="symbol", values="volume_usd").sort_index().ffill(limit=5)
    data_as_of = close.index.max()
    periods = close.index.to_period("M")
    completed_periods = sorted(p for p in periods.unique() if p < data_as_of.to_period("M"))
    signal_dates = [close.index[periods == period].max() for period in completed_periods]
    historical = [_feature_snapshot(close, volume, date) for date in signal_dates]
    historical = pd.concat([f for f in historical if not f.empty], ignore_index=True) if any(not f.empty for f in historical) else pd.DataFrame()
    current = _feature_snapshot(close, volume, data_as_of)
    save_df(historical, DATA_PROCESSED / "qos_v2a_monthly_features.csv")
    save_df(current, DATA_PROCESSED / "qos_v2a_current_features.csv")
    return historical, close, current, data_as_of


def get_weights_for_date(features_at_date: pd.DataFrame, strategy_name: str) -> tuple[dict, list, str]:
    config = CFG["strategies"][strategy_name].copy()
    regime = features_at_date["btc_regime"].iloc[0] if not features_at_date.empty else "UNKNOWN"
    if regime != "RISK_ON":
        cut = config["alts"] * 0.5
        config["alts"] -= cut
        config["cash"] += cut
    ranking = features_at_date[
        ~features_at_date["is_core"] & ~features_at_date["is_stable"] & ~features_at_date["is_blocked"]
    ].sort_values("score", ascending=False)
    picks = ranking.head(int(config["n_alts"]))["symbol"].tolist()
    weights = {"BTC": config["btc"], "ETH": config["eth"], "CASH": config["cash"]}
    if picks:
        for symbol in picks:
            weights[symbol] = config["alts"] / len(picks)
    else:
        weights["CASH"] += config["alts"]
    return weights, picks, regime


def run_backtest(features: pd.DataFrame, close: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily_returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
    signal_dates = sorted(pd.to_datetime(features["signal_date"].drop_duplicates()))
    if not signal_dates:
        raise RuntimeError("No completed-month signals available")
    last_date = close.index.max()
    cash_daily = (1 + float(CFG["stable_return_annual"])) ** (1 / 365) - 1
    cost_per_traded_notional = (float(CFG["fee_bps_per_rebalance_trade"]) + float(CFG["slippage_bps_per_rebalance_trade"])) / 10_000
    strategies = list(CFG["strategies"]) + ["BTC_puro", "BTC_ETH_70_30", "Victor_proxy"]
    equity_rows, allocation_rows, trade_rows, summaries = [], [], [], []
    for strategy in strategies:
        equity = INITIAL
        peak = INITIAL
        max_drawdown = 0.0
        previous = {}
        strategy_equity_rows = []
        for index, signal_date in enumerate(signal_dates):
            next_signal = signal_dates[index + 1] if index + 1 < len(signal_dates) else last_date
            execution_candidates = close.index[close.index > signal_date]
            if execution_candidates.empty:
                continue
            execution_date = execution_candidates.min()
            if strategy.startswith("QOS"):
                snapshot = features[pd.to_datetime(features["signal_date"]) == signal_date]
                weights, picks, regime = get_weights_for_date(snapshot, strategy)
            elif strategy == "BTC_puro":
                weights, picks, regime = {"BTC": 1.0}, [], "BENCHMARK"
            elif strategy == "BTC_ETH_70_30":
                weights, picks, regime = {"BTC": 0.7, "ETH": 0.3}, [], "BENCHMARK"
            else:
                weights = {asset: weight for asset, weight in VICTOR_PROXY.items() if asset == "CASH" or asset in close.columns}
                total = sum(weights.values())
                weights = {asset: weight / total for asset, weight in weights.items()}
                picks, regime = [], "STATIC_PROXY"
            keys = set(previous) | set(weights)
            traded_notional = sum(abs(weights.get(key, 0) - previous.get(key, 0)) for key in keys) if previous else sum(abs(v) for v in weights.values())
            cost_fraction = traded_notional * cost_per_traded_notional
            equity *= max(0.0, 1.0 - cost_fraction)
            one_way_turnover = traded_notional / 2 if previous else traded_notional
            bought = [key for key in weights if key != "CASH" and weights.get(key, 0) > previous.get(key, 0)]
            sold = [key for key in previous if key != "CASH" and weights.get(key, 0) < previous.get(key, 0)]
            trade_rows.append({
                "signal_date": signal_date, "execution_date": execution_date, "strategy": strategy,
                "regime": regime, "bought": ";".join(bought), "sold": ";".join(sold),
                "weights": json.dumps(weights, sort_keys=True), "traded_notional": traded_notional,
                "one_way_turnover": one_way_turnover, "cost_fraction": cost_fraction,
            })
            for asset, weight in weights.items():
                allocation_rows.append({"signal_date": signal_date, "execution_date": execution_date, "strategy": strategy, "asset": asset, "weight": weight, "regime": regime})
            previous = weights
            holding_dates = close.index[(close.index > signal_date) & (close.index <= next_signal)]
            if index + 1 == len(signal_dates):
                holding_dates = close.index[(close.index > signal_date) & (close.index <= last_date)]
            for date in holding_dates:
                portfolio_return = 0.0
                for asset, weight in weights.items():
                    if asset == "CASH":
                        portfolio_return += weight * cash_daily
                    elif asset in daily_returns:
                        value = daily_returns.at[date, asset]
                        if pd.notna(value):
                            portfolio_return += weight * float(value)
                equity *= 1 + portfolio_return
                peak = max(peak, equity)
                drawdown = equity / peak - 1
                max_drawdown = min(max_drawdown, drawdown)
                row = {"date": date, "strategy": strategy, "equity_brl": equity, "drawdown": drawdown}
                strategy_equity_rows.append(row)
                equity_rows.append(row)
        strategy_frame = pd.DataFrame(strategy_equity_rows)
        final = strategy_frame["equity_brl"].iloc[-1] if not strategy_frame.empty else np.nan
        years = (strategy_frame["date"].iloc[-1] - strategy_frame["date"].iloc[0]).days / 365.25 if not strategy_frame.empty else np.nan
        cagr = (final / INITIAL) ** (1 / years) - 1 if np.isfinite(years) and years > 0 else np.nan
        daily = strategy_frame["equity_brl"].pct_change(fill_method=None).dropna() if not strategy_frame.empty else pd.Series(dtype=float)
        daily_std = float(daily.std(ddof=1)) if len(daily) > 1 else float("nan")
        annualized_volatility = daily_std * math.sqrt(365) if np.isfinite(daily_std) else float("nan")
        product_sharpe = cagr / annualized_volatility if np.isfinite(cagr) and np.isfinite(annualized_volatility) and annualized_volatility > 0 else float("nan")
        risk_free_daily = (1 + float(CFG["stable_return_annual"])) ** (1 / 365) - 1
        standard_sharpe = ((float(daily.mean()) - risk_free_daily) / daily_std * math.sqrt(365)) if np.isfinite(daily_std) and daily_std > 0 else float("nan")
        calmar = cagr / abs(max_drawdown) if np.isfinite(cagr) and max_drawdown < 0 else float("nan")
        strategy_trades = [row for row in trade_rows if row["strategy"] == strategy]
        strategy_type = "QOS_DYNAMIC_MONTHLY" if strategy.startswith("QOS") else ("PUBLIC_BENCHMARK" if strategy in {"BTC_puro", "BTC_ETH_70_30"} else "STATIC_USER_PROXY")
        summaries.append({
            "strategy": strategy, "start": strategy_frame["date"].min() if not strategy_frame.empty else None,
            "end": strategy_frame["date"].max() if not strategy_frame.empty else None,
            "final_brl": final, "final_multiple": final / INITIAL if np.isfinite(final) else np.nan,
            "cagr": cagr, "max_drawdown": max_drawdown, "ruin_touch_80dd": max_drawdown <= -0.80,
            "annualized_volatility": annualized_volatility,
            "product_compatible_sharpe_rf0": product_sharpe,
            "standard_daily_sharpe_rf_adjusted": standard_sharpe,
            "calmar_cagr_over_abs_maxdd": calmar,
            "total_cost_return_sum": float(sum(float(row["cost_fraction"]) for row in strategy_trades)),
            "total_one_way_turnover": float(sum(float(row["one_way_turnover"]) for row in strategy_trades)),
            "rebalance_events": len(strategy_trades),
            "strategy_type": strategy_type,
            "execution_lag": "next_daily_bar", "survivorship_bias_present": True,
            "evidence_status": "RESEARCH_ONLY_NOT_PROMOTED",
        })
    equity_frame = pd.DataFrame(equity_rows)
    allocation_frame = pd.DataFrame(allocation_rows)
    trade_frame = pd.DataFrame(trade_rows)
    summary_frame = pd.DataFrame(summaries)
    save_df(equity_frame, OUT / "qos_v2a_equity_curves.csv")
    save_df(allocation_frame, OUT / "qos_v2a_monthly_allocations.csv")
    save_df(trade_frame, OUT / "qos_v2a_buy_sell_log.csv")
    save_df(summary_frame, OUT / "qos_v2a_summary.csv")
    return equity_frame, allocation_frame, trade_frame, summary_frame


def current_signal(current_features: pd.DataFrame, data_as_of: pd.Timestamp) -> pd.DataFrame:
    ranking = current_features[
        ~current_features["is_core"] & ~current_features["is_stable"] & ~current_features["is_blocked"]
    ].sort_values("score", ascending=False)
    save_df(ranking.head(50), OUT / "qos_v2a_current_ranking_top50.csv")
    rows = []
    execution_eligible_from = data_as_of + pd.Timedelta(days=1)
    for strategy in CFG["strategies"]:
        weights, picks, regime = get_weights_for_date(current_features, strategy)
        for asset, weight in weights.items():
            rows.append({
                "data_as_of": data_as_of, "signal_period": str(data_as_of.to_period("M")),
                "partial_period": True, "execution_eligible_from": execution_eligible_from,
                "strategy": strategy, "regime": regime, "asset": asset, "weight": weight,
            })
    frame = pd.DataFrame(rows)
    save_df(frame, OUT / "qos_v2a_current_portfolios.csv")
    return frame


def reference_compositions(available_symbols: object, data_as_of: pd.Timestamp) -> pd.DataFrame:
    """Explain the three non-QOS rows that appear in the long-horizon scoreboard."""
    available = {str(symbol) for symbol in available_symbols} | {"BTC", "ETH", "CASH"}
    definitions = {
        "BTC_puro": ({"BTC": 1.0}, "PUBLIC_BENCHMARK", "constant target; no discretionary signal"),
        "BTC_ETH_70_30": ({"BTC": 0.70, "ETH": 0.30}, "PUBLIC_BENCHMARK", "constant 70/30 target model"),
        "Victor_proxy": (
            {asset: weight for asset, weight in VICTOR_PROXY.items() if asset in available},
            "STATIC_USER_PROXY",
            "static proxy supplied for research; not an audited real ledger",
        ),
    }
    rows: list[dict[str, object]] = []
    for strategy, (weights, strategy_type, model) in definitions.items():
        total = sum(weights.values())
        normalized = {asset: weight / total for asset, weight in weights.items()} if total else {}
        for asset, weight in normalized.items():
            rows.append(
                {
                    "data_as_of": data_as_of,
                    "strategy": strategy,
                    "strategy_type": strategy_type,
                    "asset": asset,
                    "weight": weight,
                    "rebalancing_model": model,
                    "is_managed_qos_portfolio": False,
                }
            )
    frame = pd.DataFrame(rows)
    save_df(frame, OUT / "qos_v2a_reference_compositions.csv")
    return frame


def v2a_bear_replay(equity: pd.DataFrame, start_date: str = "2025-10-06") -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    frame = equity.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for strategy, group in frame.sort_values("date").groupby("strategy"):
        window = group[group["date"] >= pd.Timestamp(start_date)].dropna(subset=["equity_brl"])
        if window.empty:
            continue
        series = pd.to_numeric(window["equity_brl"], errors="coerce").dropna()
        drawdown = series.div(series.cummax()).sub(1)
        rows.append(
            {
                "strategy": strategy,
                "start": window.iloc[0]["date"].date().isoformat(),
                "end": window.iloc[-1]["date"].date().isoformat(),
                "bear_return": float(series.iloc[-1] / series.iloc[0] - 1),
                "bear_max_drawdown": float(drawdown.min()),
                "evidence": "V2A_DAILY_EQUITY_CURRENT_RUN",
            }
        )
    result = pd.DataFrame(rows).sort_values("bear_return", ascending=False)
    save_df(result, OUT / "qos_v2a_bear_replay.csv")
    return result


def v2a_monte_carlo(equity: pd.DataFrame, fixture_mode: bool) -> pd.DataFrame:
    """Block-bootstrap each of the seven valid long-horizon V2A/reference curves."""
    paths = 1000 if fixture_mode else int(CFG.get("monte_carlo_paths", 10000))
    horizon = int(CFG.get("monte_carlo_horizon_days", 365))
    block = int(CFG.get("monte_carlo_block_days", 5))
    rows: list[dict[str, object]] = []
    for strategy, group in equity.sort_values("date").groupby("strategy"):
        clean = pd.to_numeric(group["equity_brl"], errors="coerce").pct_change(fill_method=None).dropna().to_numpy()
        if len(clean) < 60:
            rows.append({"strategy": strategy, "status": "INSUFFICIENT_HISTORY", "observations": len(clean)})
            continue
        rng = np.random.default_rng(int(CFG.get("random_seed", 20260719)) + sum(ord(char) for char in strategy))
        totals = np.empty(paths)
        max_drawdowns = np.empty(paths)
        for index in range(paths):
            sampled: list[float] = []
            while len(sampled) < horizon:
                start = int(rng.integers(0, max(1, len(clean) - block + 1)))
                sampled.extend(clean[start : start + block])
            path_returns = np.asarray(sampled[:horizon])
            path_equity = np.cumprod(1 + path_returns)
            totals[index] = path_equity[-1] - 1
            max_drawdowns[index] = np.min(path_equity / np.maximum.accumulate(path_equity) - 1)
        rows.append(
            {
                "strategy": strategy,
                "status": "LONG_HISTORY_BLOCK_BOOTSTRAP_SCENARIO_ONLY",
                "observations": len(clean),
                "paths": paths,
                "horizon_days": horizon,
                "block_days": block,
                "return_p05": float(np.quantile(totals, 0.05)),
                "return_p25": float(np.quantile(totals, 0.25)),
                "return_p50": float(np.quantile(totals, 0.50)),
                "return_p75": float(np.quantile(totals, 0.75)),
                "return_p95": float(np.quantile(totals, 0.95)),
                "probability_loss": float(np.mean(totals < 0)),
                "max_drawdown_p50": float(np.quantile(max_drawdowns, 0.50)),
                "max_drawdown_p05_worse_tail": float(np.quantile(max_drawdowns, 0.05)),
                "decision_role": "SCENARIO_ENGINE_NOT_ALPHA",
            }
        )
    result = pd.DataFrame(rows)
    save_df(result, OUT / "qos_v2a_monte_carlo_10000_summary.csv")
    return result


def make_charts(equity: pd.DataFrame, summary: pd.DataFrame) -> None:
    if plt is None or equity.empty:
        return
    figure, axis = plt.subplots(figsize=(11, 6))
    for strategy, group in equity.groupby("strategy"):
        axis.plot(group["date"], group["equity_brl"], label=strategy)
    axis.set_title("QOS V2A v0.4 - curvas sem retorno no candle do sinal")
    axis.set_ylabel("BRL nominal de estudo")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(OUT / "qos_v2a_equity_curves.png", dpi=150)
    plt.close(figure)


def validated_zip(source_root: Path, output_zip: Path) -> None:
    temporary = output_zip.with_suffix(".partial.zip")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(source_root).as_posix())
    with zipfile.ZipFile(temporary, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt V2A output entry: {bad}")
    os.replace(temporary, output_zip)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-mode", action="store_true", help="deterministic offline integration fixture")
    parser.add_argument("--output-zip", default="/content/qos_v2a_outputs_v04.zip")
    args = parser.parse_args(argv)
    reset_run_dirs()
    manifest = {
        "version": VERSION, "run_utc": utc_now(),
        "mode": "offline_fixture_no_network" if args.fixture_mode else "public_data_no_api_key_no_orders",
        "technical_status": "RUNNING", "data_quality_status": "PENDING",
        "evidence_status": "RESEARCH_ONLY_NOT_PROMOTED", "operational_status": "NOT_APPROVED",
        "errors": [], "warnings": ["current-universe survivorship bias remains; point-in-time universe is not yet available"],
    }
    try:
        if args.fixture_mode:
            master = build_fixture_master()
            failures = pd.DataFrame(columns=["symbol", "reason"])
            attempted = master["symbol"].nunique()
        else:
            session = session_or_raise()
            universe = fetch_coingecko_universe(session, int(CFG["top_n_coingecko"]))
            master, failures = fetch_candles_for_universe(session, universe)
            attempted = min(int(CFG["max_assets_to_fetch"]), len(universe))
        if master.empty or not {"BTC", "ETH"}.issubset(set(master["symbol"])):
            raise RuntimeError("V2A data gate failed: BTC/ETH histories are mandatory")
        features, close, current_features, data_as_of = compute_monthly_features(master)
        if features.empty or current_features.empty:
            raise RuntimeError("V2A feature gate failed")
        equity, allocations, trades, summary = run_backtest(features, close)
        current = current_signal(current_features, data_as_of)
        references = reference_compositions(close.columns, data_as_of)
        bear_replay = v2a_bear_replay(equity)
        monte_carlo = v2a_monte_carlo(equity, args.fixture_mode)
        make_charts(equity, summary)
        loaded_symbols = master["symbol"].nunique()
        coverage = loaded_symbols / max(1, attempted)
        data_status = "PASS" if args.fixture_mode or (loaded_symbols >= 30 and coverage >= 0.45) else "PARTIAL_DATA_WARNING"
        manifest.update({
            "technical_status": "PASS", "data_quality_status": data_status,
            "data_as_of": str(data_as_of.date()), "attempted_symbols": attempted,
            "loaded_symbols": loaded_symbols, "failed_symbols": len(failures), "coverage_ratio": coverage,
            "historical_signal_rows": len(features), "current_feature_rows": len(current_features),
            "equity_rows": len(equity), "current_portfolio_rows": len(current),
            "reference_composition_rows": len(references),
            "bear_replay_rows": len(bear_replay),
            "monte_carlo_rows": len(monte_carlo),
            "long_horizon_scoreboard_rows": len(summary),
            "lookahead_guard": "signals execute on next daily bar",
            "partial_month_guard": "current month excluded from historical backtest",
            "portfolio_roles": {
                "managed_qos": 4,
                "public_benchmarks": 2,
                "static_user_proxy": 1,
            },
            "monte_carlo_role": "SCENARIO_ENGINE_NOT_ALPHA",
        })
        save_df(pd.DataFrame([{
            "data_as_of": data_as_of, "attempted_symbols": attempted, "loaded_symbols": loaded_symbols,
            "failed_symbols": len(failures), "coverage_ratio": coverage, "data_quality_status": data_status,
            "survivorship_bias_present": True,
        }]), OUT / "data_quality_summary.csv")
        (OUT / "EVIDENCE_STATUS.md").write_text(
            "# V2A evidence status\n\n"
            "- Technical execution: PASS\n"
            f"- Data quality: {data_status}\n"
            "- Historical execution: next daily bar after signal close\n"
            "- Current-universe survivorship bias: PRESENT\n"
            "- Operational promotion: NOT APPROVED\n",
            encoding="utf-8",
        )
        save_json(manifest, OUT / "v2a_run_manifest.json")
        validated_zip(ROOT, Path(args.output_zip))
        print(f"ZIP_READY: {args.output_zip}", flush=True)
        return 0
    except Exception as exc:
        manifest["technical_status"] = "FAIL"
        manifest["data_quality_status"] = "NOT_EVALUATED"
        manifest["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        save_json(manifest, OUT / "v2a_run_manifest.json")
        print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
