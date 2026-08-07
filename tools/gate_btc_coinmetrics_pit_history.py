#!/usr/bin/env python3
"""Public Coin Metrics daily history adapter for the GATE BTC definitive PIT audit.

Uses the Community API only (no key) and resolves CMC historical identities
against Coin Metrics reference-data/assets by exact normalized full name and
unique ticker-compatible IDs. Ambiguous identities remain unresolved and in
the PIT coverage denominator; they never enter the strategy selection.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Any

import pandas as pd
import requests

CM_ROOT = "https://community-api.coinmetrics.io/v4"
START = "2019-12-01"
END = "2026-08-06"
PRICE_METRIC = "PriceUSD"
VOLUME_METRIC = "volume_reported_spot_usd_1d"


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def get(session: requests.Session, url: str, params: dict | None = None, tries: int = 7) -> requests.Response:
    last = None
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=60)
            last = response
            if response.status_code == 200:
                return response
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(min(15.0, 1.25 * (attempt + 1)))
                continue
            response.raise_for_status()
        except Exception:
            if attempt + 1 == tries:
                raise
            time.sleep(min(15.0, 1.25 * (attempt + 1)))
    raise RuntimeError(f"Coin Metrics HTTP failure status={getattr(last, 'status_code', None)} url={url}")


def get_all(session: requests.Session, path: str, params: dict | None = None) -> list[dict[str, Any]]:
    url = CM_ROOT + path
    query = dict(params or {})
    query.setdefault("page_size", 10000)
    rows: list[dict[str, Any]] = []
    while url:
        response = get(session, url, query if url.startswith(CM_ROOT) else None)
        payload = response.json()
        rows.extend(payload.get("data") or [])
        next_url = payload.get("next_page_url")
        if next_url:
            url = next_url.replace("https://api.coinmetrics.io/v4", CM_ROOT)
            query = None
        else:
            url = ""
    return rows


def asset_reference(session: requests.Session) -> pd.DataFrame:
    rows = get_all(session, "/reference-data/assets", {"page_size": 10000})
    frame = pd.DataFrame(rows)
    if frame.empty or not {"asset", "full_name"}.issubset(frame.columns):
        raise RuntimeError("Coin Metrics reference-data/assets unavailable")
    frame = frame[["asset", "full_name"]].dropna().drop_duplicates().copy()
    frame["asset"] = frame["asset"].astype(str).str.strip()
    frame["full_name"] = frame["full_name"].astype(str).str.strip()
    frame["name_norm"] = frame["full_name"].map(norm)
    return frame


def metric_catalog(session: requests.Session) -> dict[str, dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]]:
    """Return only metrics actually available to the no-key Community plan."""
    rows = get_all(session, "/catalog-v2/asset-metrics", {"page_size": 10000})
    output: dict[str, dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]] = defaultdict(dict)
    for row in rows:
        asset = str(row.get("asset") or "").strip()
        if not asset:
            continue
        for metric in row.get("metrics") or []:
            name = metric.get("metric")
            if name not in {PRICE_METRIC, VOLUME_METRIC}:
                continue
            for freq in metric.get("frequencies") or []:
                if freq.get("frequency") != "1d":
                    continue
                mn = pd.to_datetime(freq.get("min_time"), utc=True, errors="coerce")
                mx = pd.to_datetime(freq.get("max_time"), utc=True, errors="coerce")
                output[asset][name] = (
                    None if pd.isna(mn) else mn.tz_localize(None),
                    None if pd.isna(mx) else mx.tz_localize(None),
                )
    return output


def resolve_cmc_to_cm(snapshots: pd.DataFrame, reference: pd.DataFrame, catalog: dict[str, dict]) -> pd.DataFrame:
    """Resolve each historical CMC symbol only when identity is unambiguous."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for row in reference.itertuples(index=False):
        if row.name_norm:
            by_name[row.name_norm].add(row.asset)
    ref_assets = set(reference["asset"])
    records = []
    for symbol, group in snapshots.groupby("symbol"):
        symbol = str(symbol)
        names = sorted(set(group["name"].astype(str)))
        name_norms = sorted(set(norm(x) for x in names if norm(x)))
        synthetic = symbol.startswith("U") and len(symbol) == 9
        candidates: set[str] = set()
        resolution_sources = []
        if not synthetic:
            lower = symbol.lower()
            if lower in ref_assets:
                candidates.add(lower)
                resolution_sources.append("CM_TICKER")
            for name_norm in name_norms:
                exact = by_name.get(name_norm, set())
                if len(exact) == 1:
                    candidates |= exact
                    resolution_sources.append("CM_FULL_NAME")
        name_candidates = set()
        for name_norm in name_norms:
            exact = by_name.get(name_norm, set())
            if len(exact) == 1:
                name_candidates |= exact
        if len(name_candidates) == 1:
            candidates = name_candidates
        cm_asset = next(iter(candidates)) if len(candidates) == 1 else ""
        metrics = catalog.get(cm_asset, {}) if cm_asset else {}
        has_price = PRICE_METRIC in metrics
        has_volume = VOLUME_METRIC in metrics
        history_usable = bool(cm_asset and has_price and has_volume and not synthetic)
        records.append({
            "symbol": symbol,
            "cmc_names": " | ".join(names),
            "cm_asset": cm_asset,
            "cm_full_name": reference.loc[reference.asset == cm_asset, "full_name"].iloc[0] if cm_asset and (reference.asset == cm_asset).any() else "",
            "candidate_count": len(candidates),
            "resolution_sources": ";".join(sorted(set(resolution_sources))),
            "cm_price_1d": has_price,
            "cm_volume_1d": has_volume,
            "history_usable": history_usable,
            "identity_confidence": "HIGH_CM_NAME" if history_usable and name_candidates == {cm_asset} else ("MEDIUM_CM_TICKER" if history_usable else "BLOCKED"),
            "first_snapshot": group["snapshot_date"].min(),
            "last_snapshot": group["snapshot_date"].max(),
            "best_rank": int(group["rank"].min()),
            "snapshot_appearances": int(group["snapshot_date"].nunique()),
        })
    return pd.DataFrame(records).sort_values(["history_usable", "best_rank", "symbol"], ascending=[False, True, True])


def fetch_asset_history(session: requests.Session, cm_asset: str) -> pd.DataFrame:
    params = {
        "assets": cm_asset,
        "metrics": f"{PRICE_METRIC},{VOLUME_METRIC}",
        "start_time": START,
        "end_time": END,
        "frequency": "1d",
        "paging_from": "start",
        "page_size": 10000,
    }
    rows = get_all(session, "/timeseries/asset-metrics", params)
    if not rows:
        return pd.DataFrame(columns=["date", "close_usd", "volume_usd"])
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["time"], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    frame["close_usd"] = pd.to_numeric(frame.get(PRICE_METRIC), errors="coerce")
    frame["volume_usd"] = pd.to_numeric(frame.get(VOLUME_METRIC), errors="coerce")
    frame = frame.dropna(subset=["date", "close_usd", "volume_usd"])
    frame = frame[(frame["close_usd"] > 0) & (frame["volume_usd"] >= 0)]
    return frame[["date", "close_usd", "volume_usd"]].drop_duplicates("date", keep="last").sort_values("date")


def collect_histories(session: requests.Session, identity: pd.DataFrame, outdir) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    coverage = []
    usable = identity[identity["history_usable"]].copy()
    for index, record in enumerate(usable.itertuples(index=False), 1):
        try:
            hist = fetch_asset_history(session, record.cm_asset)
            status = "PASS" if len(hist) >= 2 else "NO_USABLE_HISTORY"
        except Exception as exc:
            hist = pd.DataFrame(columns=["date", "close_usd", "volume_usd"])
            status = f"ERROR:{type(exc).__name__}"
        if not hist.empty:
            hist = hist.copy()
            hist["symbol"] = record.symbol
            rows.append(hist[["date", "symbol", "close_usd", "volume_usd"]])
        coverage.append({
            "symbol": record.symbol,
            "cm_asset": record.cm_asset,
            "status": status,
            "rows": len(hist),
            "first_date": hist["date"].min() if not hist.empty else None,
            "last_date": hist["date"].max() if not hist.empty else None,
        })
        print(f"CM {index}/{len(usable)} {record.symbol}->{record.cm_asset} rows={len(hist)} {status}", flush=True)
        time.sleep(0.015)
    master = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd"])
    master["source"] = "coinmetrics_community"
    master.to_csv(outdir / "COINMETRICS_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov = pd.DataFrame(coverage)
    cov.to_csv(outdir / "COINMETRICS_COVERAGE.csv", index=False)
    return master, cov


def build_identity_and_histories(session: requests.Session, snapshots: pd.DataFrame, outdir) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reference = asset_reference(session)
    reference.to_csv(outdir / "COINMETRICS_ASSET_REFERENCE.csv", index=False)
    catalog = metric_catalog(session)
    identity = resolve_cmc_to_cm(snapshots, reference, catalog)
    identity.to_csv(outdir / "IDENTITY_AUDIT.csv", index=False)
    master, coverage = collect_histories(session, identity, outdir)
    return identity, master, coverage
