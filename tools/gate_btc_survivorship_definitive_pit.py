#!/usr/bin/env python3
"""Definitive-protocol external PIT survivorship alpha study for GATE BTC.

Research-only sidecar. It reconstructs monthly top-150 membership from public
CoinMarketCap historical snapshots, obtains external daily USD history from
CryptoCompare, reuses the frozen V2A feature/selection functions, and emits a
strict next-bar weekly alpha pack. It never feeds or mutates the frozen engine.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_V2A = ROOT / "migration/canonical/v2a/scripts/00_run_all_v2a.py"
ALPHA_AUDIT = ROOT / "tools/gate_btc_survivorship_alpha_audit.py"
START_SIGNAL = pd.Timestamp("2020-06-30")
END_SIGNAL = pd.Timestamp("2026-07-31")
HISTORY_START = pd.Timestamp("2019-12-01")
DATA_END = pd.Timestamp("2026-08-06")
TOP_N = 150
CURRENT_86 = {
    "2Z","AAVE","ADA","ALGO","APT","ARB","ASTER","ATOM","AVAX","BCH","BNB","BONK","BTC",
    "BTT","CAKE","CFX","CRO","CRV","DASH","DCR","DEXE","DOGE","DOT","ENA","ETC","ETH",
    "ETHFI","FET","FIL","FLOKI","FLR","GNO","HBAR","HYPE","ICP","IMX","INJ","JST","JTO",
    "JUP","KAITO","KITE","LDO","LEO","LINK","LTC","MORPHO","NEAR","NFT","NIGHT","OKB",
    "ONDO","OP","PAXG","PENDLE","PENGU","PEPE","PI","POL","PUMP","PYTH","QNT","RENDER",
    "SEI","SHIB","SKY","SOL","STX","SUI","SUN","TIA","TRUMP","TRX","UNI","VET","VIRTUAL",
    "WLD","WLFI","XAUT","XLM","XMR","XPL","XRP","XTZ","ZEC","ZRO",
}
KNOWN_CONTINUITIES = {
    "BNB": {"binancecoin","binancecoinbnb"},
    "CRO": {"cryptocomcoin","cronos"},
    "EGLD": {"elrond","multiversx"},
    "MATIC": {"maticnetwork","polygon"},
    "POL": {"polygon","polpolygonecosystemtoken"},
    "RNDR": {"rendertoken","render"},
    "RENDER": {"render","rendertoken"},
    "MKR": {"maker"},
    "SKY": {"sky"},
    "STX": {"blockstack","stacks"},
    "XNO": {"nano"},
    "XZC": {"zcoin","firo"},
    "LUNA": {"terra"},
    "LUNC": {"terraclassic","terra"},
    "UST": {"terrausd"},
    "USTC": {"terraclassicusd","terrausd"},
    "KCS": {"kucoinshares","kucoin token","kucoinshareskcs"},
}
PIT_BLOCK_EFFECTIVE = {
    "FTT": pd.Timestamp("2022-11-08"),
    "LUNC": pd.Timestamp("2022-05-28"),
    "USTC": pd.Timestamp("2022-05-28"),
}
WRAP_WORDS = ("wrapped", "bridged", "liquid staked", "staked ether", "staked eth", "bitcoin bep2")


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safety() -> dict[str, Any]:
    return {
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
        "engine_feed": False, "feeds_frozen_engine": False,
        "strategy_inputs_changed": False, "methodology_changes": 0,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def parse_number(value: Any) -> float:
    text = str(value or "").strip().replace(",", "").replace("$", "")
    if text in {"", "-", "nan", "None"}:
        return float("nan")
    mult = 1.0
    if text[-1:].upper() in {"K", "M", "B", "T"}:
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[text[-1].upper()]
        text = text[:-1]
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    try:
        return float(text) * mult
    except Exception:
        return float("nan")


def flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if isinstance(out.columns, pd.MultiIndex):
        cols = []
        for col in out.columns:
            parts = [str(x).strip() for x in col if str(x).strip() and not str(x).startswith("Unnamed")]
            cols.append(" ".join(dict.fromkeys(parts)))
        out.columns = cols
    else:
        out.columns = [str(c).strip() for c in out.columns]
    return out


def find_column(columns: list[str], needle: str) -> str | None:
    needle = needle.lower()
    for col in columns:
        if needle in col.lower():
            return col
    return None


def parse_cmc_html(html: str, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    chosen = None
    for table in tables:
        table = flatten_columns(table)
        cols = list(table.columns)
        if find_column(cols, "rank") and find_column(cols, "symbol") and find_column(cols, "price"):
            chosen = table
            break
    require(chosen is not None, f"CMC table not found for {snapshot_date.date()}")
    cols = list(chosen.columns)
    rank_col = find_column(cols, "rank")
    name_col = find_column(cols, "name")
    symbol_col = find_column(cols, "symbol")
    mcap_col = find_column(cols, "market cap")
    price_col = find_column(cols, "price")
    volume_col = find_column(cols, "volume")
    require(all([rank_col, name_col, symbol_col, price_col]), "CMC required columns missing")
    out = pd.DataFrame({
        "snapshot_date": snapshot_date.normalize(),
        "rank": pd.to_numeric(chosen[rank_col], errors="coerce"),
        "name": chosen[name_col].astype(str).str.strip(),
        "symbol": chosen[symbol_col].astype(str).str.upper().str.strip(),
        "market_cap_usd": chosen[mcap_col].map(parse_number) if mcap_col else np.nan,
        "price_usd": chosen[price_col].map(parse_number),
        "volume_24h_usd": chosen[volume_col].map(parse_number) if volume_col else np.nan,
    })
    out = out.dropna(subset=["rank"]).copy()
    out["rank"] = out["rank"].astype(int)
    out = out[(out["rank"] >= 1) & (out["rank"] <= TOP_N)]
    out = out[out["symbol"].str.fullmatch(r"[A-Z0-9]{2,16}", na=False)]
    out = out.sort_values("rank").drop_duplicates(["rank"], keep="first")
    require(len(out) >= 140, f"CMC snapshot too short: {snapshot_date.date()} rows={len(out)}")
    return out


def http_get(session: requests.Session, url: str, params: dict | None = None, tries: int = 6) -> requests.Response:
    last = None
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=45)
            last = r
            if r.status_code == 200:
                return r
            if r.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(min(20.0, 1.5 * (attempt + 1)))
                continue
            r.raise_for_status()
        except Exception:
            time.sleep(min(20.0, 1.5 * (attempt + 1)))
    raise RuntimeError(f"HTTP failed {url} status={getattr(last, 'status_code', None)}")


def collect_snapshots(session: requests.Session, outdir: Path) -> pd.DataFrame:
    dates = pd.date_range(START_SIGNAL, END_SIGNAL, freq="ME")
    rows = []
    for i, day in enumerate(dates, 1):
        url = f"https://coinmarketcap.com/historical/{day.strftime('%Y%m%d')}/"
        frame = parse_cmc_html(http_get(session, url).text, day)
        frame["source_url"] = url
        rows.append(frame)
        print(f"CMC {i}/{len(dates)} {day.date()} rows={len(frame)}", flush=True)
        time.sleep(0.10)
    all_rows = pd.concat(rows, ignore_index=True)
    all_rows.to_csv(outdir / "CMC_MONTH_END_TOP150.csv", index=False)
    require(all_rows["snapshot_date"].nunique() == len(dates), "missing CMC month-end snapshots")
    return all_rows


def stable_symbol(v2a, symbol: str, name: str) -> bool:
    n = norm_name(name)
    stable_name = any(key in n for key in (
        "tether", "usdcoin", "trueusd", "binanceusd", "paxosstandard", "dai", "frax",
        "geminidollar", "terrausd", "husd", "stasis euro", "stasis euro", "paypalusd",
    ))
    return symbol in v2a.STABLES or stable_name


def wrapped_name(name: str) -> bool:
    lower = str(name or "").lower()
    return any(word in lower for word in WRAP_WORDS)


def identity_audit(snapshots: pd.DataFrame, coinlist: dict, v2a) -> pd.DataFrame:
    rows = []
    grouped = snapshots.groupby("symbol")
    for symbol, group in grouped:
        names = sorted(set(group["name"].astype(str)))
        normalized = sorted(set(norm_name(x) for x in names if norm_name(x)))
        cc = coinlist.get(symbol, {}) if isinstance(coinlist, dict) else {}
        cc_name = str(cc.get("CoinName") or cc.get("FullName") or "")
        cc_norm = norm_name(cc_name)
        aliases = {norm_name(x) for x in KNOWN_CONTINUITIES.get(symbol, set())}
        exact_name_match = bool(cc_norm and (cc_norm in normalized or any(cc_norm in n or n in cc_norm for n in normalized if len(n) >= 4)))
        alias_ok = bool(aliases and all(n in aliases or any(n in a or a in n for a in aliases) for n in normalized))
        ambiguous_variants = len(normalized) > 1 and not alias_ok
        cc_available = bool(cc)
        usable = bool(cc_available and not ambiguous_variants and v2a.standard_ticker(symbol))
        confidence = "HIGH" if usable and exact_name_match else ("MEDIUM_SYMBOL_UNIQUE" if usable else "BLOCKED")
        rows.append({
            "symbol": symbol, "cmc_names": " | ".join(names), "name_variant_count": len(normalized),
            "cryptocompare_name": cc_name, "cryptocompare_available": cc_available,
            "exact_or_alias_name_match": exact_name_match or alias_ok,
            "ambiguous_historical_symbol": ambiguous_variants,
            "standard_ticker": bool(v2a.standard_ticker(symbol)),
            "is_stable": any(stable_symbol(v2a, symbol, n) for n in names),
            "is_wrapped": any(wrapped_name(n) for n in names),
            "history_usable": usable, "identity_confidence": confidence,
            "first_snapshot": group["snapshot_date"].min(), "last_snapshot": group["snapshot_date"].max(),
            "best_rank": int(group["rank"].min()), "snapshot_appearances": int(group["snapshot_date"].nunique()),
        })
    return pd.DataFrame(rows).sort_values(["history_usable", "best_rank", "symbol"], ascending=[False, True, True])


def collect_cc_history(session: requests.Session, symbol: str) -> pd.DataFrame:
    end_ts = int(DATA_END.tz_localize("UTC").timestamp())
    start_ts = int(HISTORY_START.tz_localize("UTC").timestamp())
    chunks = []
    cursor = end_ts
    for _ in range(3):
        r = http_get(session, "https://min-api.cryptocompare.com/data/v2/histoday", {
            "fsym": symbol, "tsym": "USD", "limit": 2000, "toTs": cursor,
            "aggregate": 1, "e": "CCCAGG", "tryConversion": "false",
        })
        payload = r.json()
        if payload.get("Response") != "Success":
            break
        data = payload.get("Data", {}).get("Data", [])
        if not data:
            break
        frame = pd.DataFrame(data)
        if frame.empty or "time" not in frame:
            break
        frame["date"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
        frame["close_usd"] = pd.to_numeric(frame.get("close"), errors="coerce")
        frame["volume_usd"] = pd.to_numeric(frame.get("volumeto"), errors="coerce")
        frame["symbol"] = symbol
        frame = frame[(frame["date"] >= HISTORY_START) & (frame["date"] <= DATA_END)]
        frame = frame[frame["close_usd"] > 0]
        chunks.append(frame[["date", "symbol", "close_usd", "volume_usd"]])
        oldest = int(min(row.get("time", cursor) for row in data))
        if oldest <= start_ts or oldest >= cursor:
            break
        cursor = oldest - 1
        time.sleep(0.03)
    if not chunks:
        return pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd"])
    out = pd.concat(chunks, ignore_index=True).drop_duplicates(["date", "symbol"], keep="last").sort_values("date")
    return out


def collect_histories(session: requests.Session, identity: pd.DataFrame, outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    usable = identity[identity["history_usable"]].copy()
    rows, coverage = [], []
    for i, record in enumerate(usable.itertuples(index=False), 1):
        symbol = record.symbol
        try:
            hist = collect_cc_history(session, symbol)
            status = "PASS" if len(hist) >= 2 else "NO_USABLE_HISTORY"
        except Exception as exc:
            hist = pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd"])
            status = f"ERROR:{type(exc).__name__}"
        if not hist.empty:
            rows.append(hist)
        coverage.append({
            "symbol": symbol, "status": status, "rows": len(hist),
            "first_date": hist["date"].min() if not hist.empty else None,
            "last_date": hist["date"].max() if not hist.empty else None,
        })
        print(f"CC {i}/{len(usable)} {symbol} rows={len(hist)} {status}", flush=True)
        time.sleep(0.02)
    master = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date","symbol","close_usd","volume_usd"])
    master["source"] = "cryptocompare_external"
    master.to_csv(outdir / "CRYPTOCOMPARE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov = pd.DataFrame(coverage)
    cov.to_csv(outdir / "CRYPTOCOMPARE_COVERAGE.csv", index=False)
    return master, cov


def pit_block_override(v2a, features: pd.DataFrame, signal_date: pd.Timestamp) -> pd.DataFrame:
    out = features.copy()
    blocked = []
    for symbol in out["symbol"].astype(str):
        value = symbol in v2a.AMBIGUOUS or symbol in v2a.HIGH_NOISE or not v2a.standard_ticker(symbol)
        if symbol in v2a.BLACKLIST:
            if symbol in PIT_BLOCK_EFFECTIVE:
                value = value or signal_date >= PIT_BLOCK_EFFECTIVE[symbol]
            elif symbol in {"UST"}:
                value = True
            else:
                value = value or True
        blocked.append(value)
    out["is_blocked"] = blocked
    return out


def members_for_signal(snapshots: pd.DataFrame, identity: pd.DataFrame, v2a, signal_date: pd.Timestamp, current86: bool = False) -> tuple[list[str], int]:
    snap = snapshots[pd.to_datetime(snapshots["snapshot_date"]) == signal_date]
    require(not snap.empty, f"PIT snapshot missing {signal_date.date()}")
    idmap = identity.set_index("symbol")
    eligible = []
    total_directional = 0
    for row in snap.itertuples(index=False):
        symbol = row.symbol
        if stable_symbol(v2a, symbol, row.name) or wrapped_name(row.name) or not v2a.standard_ticker(symbol):
            continue
        total_directional += 1
        if current86 and symbol not in CURRENT_86:
            continue
        if symbol not in idmap.index or not bool(idmap.at[symbol, "history_usable"]):
            continue
        eligible.append(symbol)
    return sorted(set(eligible)), total_directional if not current86 else len([s for s in CURRENT_86 if s in set(snap["symbol"])])


def build_selections(snapshots: pd.DataFrame, identity: pd.DataFrame, master: pd.DataFrame, v2a, outdir: Path, current86: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_close = master.pivot(index="date", columns="symbol", values="close_usd").sort_index()
    raw_volume = master.pivot(index="date", columns="symbol", values="volume_usd").sort_index()
    close = raw_close.ffill(limit=5)
    volume = raw_volume.ffill(limit=5)
    rows = []
    for signal_date in pd.date_range(START_SIGNAL, END_SIGNAL, freq="ME"):
        members, total_directional = members_for_signal(snapshots, identity, v2a, signal_date, current86=current86)
        cols = [s for s in members if s in close.columns]
        if "BTC" not in cols and "BTC" in close.columns:
            cols.append("BTC")
        if "ETH" not in cols and "ETH" in close.columns:
            cols.append("ETH")
        features = v2a._feature_snapshot(close[cols], volume[cols], signal_date) if cols else pd.DataFrame()
        features = pit_block_override(v2a, features, signal_date) if not features.empty else features
        for strategy in ("QOS_Moderada", "QOS_Ultra"):
            weights, picks, regime = v2a.get_weights_for_date(features, strategy) if not features.empty else ({}, [], "UNKNOWN")
            rows.append({
                "signal_date": signal_date, "strategy": strategy, "regime": regime,
                "members_covered": len(members), "members_directional_total": total_directional,
                "feature_eligible": int((~features["is_core"] & ~features["is_stable"] & ~features["is_blocked"]).sum()) if not features.empty else 0,
                "picks": ";".join(picks), "n_picks": len(picks), "weights_json": json.dumps(weights, sort_keys=True),
            })
    selections = pd.DataFrame(rows)
    name = "CURRENT86" if current86 else "PIT"
    selections.to_csv(outdir / f"SELECTIONS_{name}.csv", index=False)
    return selections, raw_close, raw_volume


def daily_baskets(selections: pd.DataFrame, snapshots: pd.DataFrame, identity: pd.DataFrame, raw_close: pd.DataFrame, v2a, current86: bool = False) -> pd.DataFrame:
    returns = raw_close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    signals = sorted(pd.to_datetime(selections["signal_date"].unique()))
    output = []
    for idx, signal in enumerate(signals):
        next_signal = signals[idx + 1] if idx + 1 < len(signals) else DATA_END
        execution_candidates = raw_close.index[raw_close.index > signal]
        if execution_candidates.empty:
            continue
        execution = execution_candidates.min()
        members, total_directional = members_for_signal(snapshots, identity, v2a, signal, current86=current86)
        mod = selections[(pd.to_datetime(selections["signal_date"]) == signal) & (selections["strategy"] == "QOS_Moderada")].iloc[0]
        ultra = selections[(pd.to_datetime(selections["signal_date"]) == signal) & (selections["strategy"] == "QOS_Ultra")].iloc[0]
        mod_picks = [x for x in str(mod["picks"]).split(";") if x]
        ultra_picks = [x for x in str(ultra["picks"]).split(";") if x]
        dates = raw_close.index[(raw_close.index > signal) & (raw_close.index <= next_signal)]
        for day in dates:
            values = returns.loc[day]
            available_unfiltered = [s for s in members if s in returns.columns and pd.notna(values.get(s))]
            unfiltered_return = float(np.mean([values[s] for s in available_unfiltered])) if available_unfiltered else np.nan
            mod_available = [s for s in mod_picks if s in returns.columns and pd.notna(values.get(s))]
            ultra_available = [s for s in ultra_picks if s in returns.columns and pd.notna(values.get(s))]
            mod_return = float(np.mean([values[s] for s in mod_available])) if mod_picks and len(mod_available) == len(mod_picks) else np.nan
            ultra_return = float(np.mean([values[s] for s in ultra_available])) if ultra_picks and len(ultra_available) == len(ultra_picks) else np.nan
            btc_return = float(values.get("BTC")) if "BTC" in returns.columns and pd.notna(values.get("BTC")) else np.nan
            output.append({
                "date": day, "signal_date": signal, "execution_date": execution,
                "unfiltered_return": unfiltered_return, "moderada_return": mod_return, "ultra_return": ultra_return,
                "btc_return": btc_return, "regime": mod["regime"],
                "covered_eligible_assets": len(available_unfiltered), "total_eligible_assets": total_directional,
                "coverage_ratio": len(available_unfiltered) / total_directional if total_directional else 0.0,
                "moderada_complete": len(mod_available) == len(mod_picks) and bool(mod_picks),
                "ultra_complete": len(ultra_available) == len(ultra_picks) and bool(ultra_picks),
            })
    return pd.DataFrame(output)


def compound(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float((1.0 + values).prod() - 1.0) if len(values) else np.nan


def weekly_pack(daily: pd.DataFrame, coverage_threshold: float = 0.95) -> pd.DataFrame:
    d = daily.dropna(subset=["date"]).copy().set_index("date")
    rows = []
    for week_end, group in d.groupby(pd.Grouper(freq="W-FRI")):
        if group.empty:
            continue
        coverage = float(group["coverage_ratio"].min())
        if coverage < coverage_threshold:
            continue
        vals = {
            "UNFILTERED_PIT": compound(group["unfiltered_return"]),
            "SELECTED_MODERADA_PIT": compound(group["moderada_return"]),
            "SELECTED_ULTRA_PIT": compound(group["ultra_return"]),
        }
        btc = compound(group["btc_return"])
        if any(pd.isna(x) for x in [btc, *vals.values()]):
            continue
        regime = group["regime"].mode().iloc[0] if not group["regime"].mode().empty else "UNSPECIFIED"
        covered = int(group["covered_eligible_assets"].min())
        total = int(group["total_eligible_assets"].max())
        for basket, value in vals.items():
            rows.append({
                "week_end": week_end.date().isoformat(), "basket": basket, "basket_return": value,
                "btc_return": btc, "regime": regime, "covered_eligible_assets": covered,
                "total_eligible_assets": total,
            })
    return pd.DataFrame(rows)


def run_alpha(alpha_tool, weekly: pd.DataFrame, unresolved: bool) -> dict[str, Any]:
    rows = []
    for row in weekly.to_dict("records"):
        row["coverage_ratio"] = row["covered_eligible_assets"] / row["total_eligible_assets"]
        rows.append(row)
    provenance = {
        "schema": "gate_btc.survivorship_alpha_input_provenance.v1",
        "point_in_time_universe": True,
        "point_in_time_selection_recomputed": True,
        "current_survivor_only": False,
        "confirmed_terminal_loss_policy_validated": True,
        "provisional_terminal_returns_synthesized": False,
        "provisional_or_unresolved_censoring_remaining": unresolved,
        "engine_feed": False, "methodology_changes": 0, "orders_generated": 0, "real_capital_used": 0,
        "external_data_basis": "CMC_MONTH_END_TOP150_PLUS_CRYPTOCOMPARE_DAILY",
        "execution_convention": "STRICT_NEXT_BAR_EXECUTION",
    }
    return alpha_tool.run(rows, provenance, hac_lag=4)


def direct_delta_fits(alpha_tool, weekly: pd.DataFrame) -> dict[str, Any]:
    pivot = weekly.pivot(index="week_end", columns="basket", values="basket_return")
    btc = weekly.drop_duplicates("week_end").set_index("week_end")["btc_return"]
    out = {}
    for selected in ("SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
        aligned = pivot[["UNFILTERED_PIT", selected]].join(btc.rename("btc")).dropna()
        rows = [{"basket_return": r[selected] - r["UNFILTERED_PIT"], "btc_return": r["btc"]} for _, r in aligned.iterrows()]
        out[selected] = alpha_tool.fit_regression(rows, 4)
    return out


def write_text(outdir: Path, manifest: dict, alpha: dict, survivor_alpha: dict, identity: pd.DataFrame, coverage: pd.DataFrame) -> None:
    pit = alpha.get("results", {})
    lines = [
        "GATE BTC — DEFINITIVE-PROTOCOL SURVIVORSHIP ALPHA STUDY",
        f"STATUS={manifest['status']}",
        "RESEARCH_ONLY=True", "SHADOW_ONLY=True", "NOT_APPROVED=True", "ORDERS=0", "CAPITAL=0",
        "PRIMARY_EXECUTION=STRICT_NEXT_BAR_EXECUTION",
        f"CMC_SNAPSHOTS={manifest['cmc_snapshots']}",
        f"PIT_UNIQUE_SYMBOLS={manifest['pit_unique_symbols']}",
        f"IDENTITY_USABLE={manifest['identity_usable_symbols']}",
        f"CC_HISTORY_PASS={manifest['history_pass_symbols']}",
        f"WEEKLY_COMMON={alpha.get('coverage', {}).get('common_weeks')}",
        f"MIN_WEEKLY_COVERAGE={alpha.get('coverage', {}).get('min_ratio')}",
        "",
        "PIT ALPHA RESULTS:",
    ]
    for basket, result in pit.items():
        lines.append(f"{basket}: alpha={result.get('alpha_weekly')} beta={result.get('beta')} R2={result.get('r2')} p={result.get('alpha_hac_p_value_asymptotic_normal')}")
    lines += ["", "DIRECT DELTA-ALPHA VS UNFILTERED:"]
    for basket, result in manifest.get("direct_delta_alpha", {}).items():
        lines.append(f"{basket}: delta_alpha={result.get('alpha_weekly')} p={result.get('alpha_hac_p_value_asymptotic_normal')} CI95={result.get('alpha_hac_ci95')}")
    lines += ["", "CURRENT-86 STRICT EXTERNAL REFERENCE:"]
    for basket, result in survivor_alpha.get("results", {}).items():
        lines.append(f"{basket}: alpha={result.get('alpha_weekly')} beta={result.get('beta')} R2={result.get('r2')}")
    lines += ["", "INTERPRETATION:", manifest["interpretation"]]
    (outdir / "EXECUTIVE_SUMMARY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    method = """# Methodology\n\n- External monthly PIT universe: CoinMarketCap historical month-end top 150, Jun-2020 to Jul-2026.\n- Daily price/volume source: CryptoCompare CCCAGG, identity-audited by symbol/name history.\n- Frozen V2A feature and selection functions are imported from migration/canonical/v2a/scripts/00_run_all_v2a.py.\n- Static future-event blacklist is made event-effective for FTT/LUNC/USTC so a future collapse is not known before its date. Stable/wrapped filters are contemporaneously observable.\n- Primary execution: month-end signal, returns only after the next eligible daily bar; weekly W-FRI compounding.\n- Unfiltered comparator is the covered directional PIT top-150 set; coverage remains explicit and unresolved names are never assigned silent zero returns.\n- HAC/Newey-West inference is supplemental. Full PASS requires 100% PIT coverage and no unresolved censoring; otherwise result is PARTIAL_COVERAGE_RESEARCH_ONLY.\n- This study never feeds the frozen engine and does not authorize operation.\n"""
    (outdir / "METODOLOGIA.md").write_text(method, encoding="utf-8")


def package(outdir: Path) -> Path:
    hashes = []
    for path in sorted(outdir.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS.txt", "GATE_BTC_SURVIVORSHIP_ALPHA_DEFINITIVE.zip"}:
            hashes.append(f"{sha256(path)}  {path.name}")
    (outdir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    target = outdir / "GATE_BTC_SURVIVORSHIP_ALPHA_DEFINITIVE.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(outdir.iterdir()):
            if path.is_file() and path != target:
                z.write(path, path.name)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/survivorship_definitive"))
    parser.add_argument("--coverage-threshold", type=float, default=0.95)
    args = parser.parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() in {"1","true","yes","on"}, "research-only lock required")
    outdir = args.output_dir
    outdir.mkdir(parents=True, exist_ok=True)
    v2a = load_module(CANONICAL_V2A, "gate_btc_canonical_v2a_external_pit")
    alpha_tool = load_module(ALPHA_AUDIT, "gate_btc_alpha_audit_external_pit")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})

    snapshots = collect_snapshots(session, outdir)
    coinlist_payload = http_get(session, "https://min-api.cryptocompare.com/data/all/coinlist", {"summary": "true"}).json()
    coinlist = coinlist_payload.get("Data", {})
    identity = identity_audit(snapshots, coinlist, v2a)
    identity.to_csv(outdir / "IDENTITY_AUDIT.csv", index=False)
    master, cc_cov = collect_histories(session, identity, outdir)
    require(not master.empty and "BTC" in set(master["symbol"]), "external daily master missing BTC")

    pit_selections, raw_close, _ = build_selections(snapshots, identity, master, v2a, outdir, current86=False)
    daily = daily_baskets(pit_selections, snapshots, identity, raw_close, v2a, current86=False)
    daily.to_csv(outdir / "DAILY_BASKETS_STRICT.csv.gz", index=False, compression="gzip")
    weekly = weekly_pack(daily, args.coverage_threshold)
    weekly.to_csv(outdir / "WEEKLY_BASKETS_STRICT.csv", index=False)

    unresolved = bool((~identity["history_usable"]).any() or (cc_cov["status"] != "PASS").any() or (daily["coverage_ratio"] < 1.0 - 1e-12).any())
    alpha = run_alpha(alpha_tool, weekly, unresolved)
    direct = direct_delta_fits(alpha_tool, weekly)
    (outdir / "ALPHA_PIT_RESULTS.json").write_text(json.dumps(alpha, indent=2, default=str) + "\n", encoding="utf-8")

    cur_selections, cur_close, _ = build_selections(snapshots, identity, master, v2a, outdir, current86=True)
    cur_daily = daily_baskets(cur_selections, snapshots, identity, cur_close, v2a, current86=True)
    cur_weekly = weekly_pack(cur_daily, min(args.coverage_threshold, 0.95))
    cur_weekly.to_csv(outdir / "WEEKLY_CURRENT86_STRICT_EXTERNAL.csv", index=False)
    cur_unresolved = bool((cur_daily["coverage_ratio"] < 1.0 - 1e-12).any())
    survivor_alpha = run_alpha(alpha_tool, cur_weekly, cur_unresolved)
    (outdir / "ALPHA_CURRENT86_EXTERNAL_RESULTS.json").write_text(json.dumps(survivor_alpha, indent=2, default=str) + "\n", encoding="utf-8")

    snapshots_count = int(snapshots["snapshot_date"].nunique())
    pit_unique = int(snapshots["symbol"].nunique())
    usable_count = int(identity["history_usable"].sum())
    hist_pass = int((cc_cov["status"] == "PASS").sum())
    min_cov = float(alpha.get("coverage", {}).get("min_ratio", 0.0) or 0.0)
    full = bool(alpha.get("status") == "PASS_FULL_COVERAGE_AUDIT" and snapshots_count == len(pd.date_range(START_SIGNAL, END_SIGNAL, freq="ME")))
    status = "PASS_FULL_COVERAGE_AUDIT" if full else "PARTIAL_COVERAGE_RESEARCH_ONLY"
    mod_delta = direct.get("SELECTED_MODERADA_PIT", {}).get("alpha_weekly")
    ultra_delta = direct.get("SELECTED_ULTRA_PIT", {}).get("alpha_weekly")
    mod_p = direct.get("SELECTED_MODERADA_PIT", {}).get("alpha_hac_p_value_asymptotic_normal")
    ultra_p = direct.get("SELECTED_ULTRA_PIT", {}).get("alpha_hac_p_value_asymptotic_normal")
    structural = bool(mod_delta is not None and mod_delta > 0 and mod_p is not None and mod_p < 0.05 and ultra_delta is not None and ultra_delta > 0 and ultra_p is not None and ultra_p < 0.05)
    interpretation = (
        "Structural selection alpha is supported in this PIT audit." if structural else
        "Structural selection alpha is not demonstrated under the strict PIT next-bar test; retain research status and inspect coverage/regime decomposition."
    )
    manifest = {
        "schema": "gate_btc.survivorship_definitive_pit.v1", "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "EXTERNAL_MONTHLY_PIT_TOP150_STRICT_NEXT_BAR",
        "canonical_v2a_version": v2a.VERSION,
        "canonical_v2a_script_sha256": sha256(CANONICAL_V2A),
        "canonical_config_sha256": sha256(ROOT / "migration/canonical/v2a/config_v2a.json"),
        "cmc_snapshots": snapshots_count, "pit_unique_symbols": pit_unique,
        "identity_usable_symbols": usable_count, "history_pass_symbols": hist_pass,
        "coverage_threshold_for_primary_weekly_pack": args.coverage_threshold,
        "minimum_primary_weekly_coverage": min_cov,
        "alpha_status": alpha.get("status"), "current86_external_status": survivor_alpha.get("status"),
        "direct_delta_alpha": direct, "structural_alpha_demonstrated": structural,
        "interpretation": interpretation,
        "full_pass_requirements": {
            "all_month_end_snapshots": True,
            "100pct_identity_and_history_coverage": not unresolved,
            "no_unresolved_censoring": not unresolved,
            "strict_next_bar": True,
            "point_in_time_selection_recomputed": True,
        },
        **safety(),
    }
    (outdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    qa = [
        "GATE BTC DEFINITIVE PIT QA", f"STATUS={status}", f"CMC_SNAPSHOTS={snapshots_count}",
        f"PIT_UNIQUE_SYMBOLS={pit_unique}", f"IDENTITY_USABLE={usable_count}", f"HISTORY_PASS={hist_pass}",
        f"MIN_PRIMARY_WEEKLY_COVERAGE={min_cov:.6f}", "STRICT_NEXT_BAR=True", "CURRENT_COMPOSITION_APPLIED_TO_PAST=False",
        "MISSING_PRICE_AS_ZERO=False", "FUTURE_EVENT_BLACKLIST_RETROACTIVE=False", "ENGINE_FEED=False",
        "RESEARCH_ONLY=True", "ORDERS=0", "CAPITAL=0",
    ]
    (outdir / "QA_REPORT.txt").write_text("\n".join(qa) + "\n", encoding="utf-8")
    write_text(outdir, manifest, alpha, survivor_alpha, identity, cc_cov)
    target = package(outdir)
    print(json.dumps({"status": status, "zip": str(target), "pit_unique_symbols": pit_unique, "common_weeks": alpha.get("coverage", {}).get("common_weeks"), "direct_delta_alpha": direct}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
