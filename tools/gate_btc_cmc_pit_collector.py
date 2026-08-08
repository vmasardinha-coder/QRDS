#!/usr/bin/env python3
"""CoinMarketCap month-end PIT collector resilient to lazy historical rendering.

Historical pages currently expose the full ordered name list but only the first
rows include materialized rank/symbol cells. Rank is therefore recovered from
verified table order and missing symbols are resolved against authoritative CMC
keyless maps, including the historical page currency-link slug, then
CryptoCompare metadata. Unresolved identities receive a stable synthetic audit
key so they remain in the coverage denominator but can never enter the strategy
selection.
"""
from __future__ import annotations

import hashlib
import re
import time
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from lxml import html as lxml_html

START_SIGNAL = pd.Timestamp("2020-06-30")
END_SIGNAL = pd.Timestamp("2026-07-31")
TOP_N = 150

HISTORICAL_NAME_ALIASES = {
    "binancecoin": "BNB",
    "cryptocomcoin": "CRO",
    "maticnetwork": "MATIC",
    "polygon": "MATIC",
    "elrond": "EGLD",
    "multiversx": "EGLD",
    "blockstack": "STX",
    "zcoin": "XZC",
    "firo": "XZC",
    "nano": "XNO",
    "raiblocks": "XRB",
    "paxosstandard": "PAX",
    "huobitoken": "HT",
    "kucoinshares": "KCS",
    "maker": "MKR",
    "rendertoken": "RNDR",
    "terra": "LUNA",
    "terrausd": "UST",
    "nem": "XEM",
    "bitcoin sv": "BSV",
    "bitcoin gold": "BTG",
    "bitcoin diamond": "BCD",
    "ethereumclassic": "ETC",
    # Conservative historical-name lineage fixes. These names are explicit
    # historical project names whose ticker is independently documented; they
    # are identity-only mappings and do not inject price/factor information.
    "fetchai": "FET",
    "voyagertoken": "VGX",
    "hederahashgraph": "HBAR",
    "swipe": "SXP",
    "kybernetwork": "KNC",
    "injectiveprotocol": "INJ",
}


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def number(value: Any) -> float:
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


def flatten(frame: pd.DataFrame) -> pd.DataFrame:
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


def find(cols: list[str], needle: str) -> str | None:
    needle = needle.lower()
    return next((col for col in cols if needle in col.lower()), None)


def get(session: requests.Session, url: str, params: dict | None = None, tries: int = 5) -> requests.Response:
    last = None
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=45)
            last = response
            if response.status_code == 200:
                return response
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(1.0 + attempt)
                continue
            response.raise_for_status()
        except Exception:
            if attempt + 1 == tries:
                raise
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"HTTP failure status={getattr(last, 'status_code', None)} url={url}")


def metadata_maps(session: requests.Session) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    # Keys intentionally include both normalized CMC names and normalized CMC
    # slugs. Historical lazy rows preserve /currencies/<slug>/ links even when
    # their symbol cell is not materialized. The slug is therefore a stronger
    # identity key than guessing from ticker text and remains keyless/auditable.
    #
    # The public CMC map endpoint is paginated (1-based `start`, max `limit`
    # 5000). Paging every listing state is required here because old top-150
    # constituents are disproportionately inactive/untracked today. Stopping at
    # the first 5000 would silently censor identity candidates before the PIT
    # history stage even starts.
    cmc_names: dict[str, set[str]] = {}
    page_size = 5000
    for status in ("active", "inactive", "untracked"):
        start = 1
        pages = 0
        total_rows = 0
        try:
            while True:
                payload = get(
                    session,
                    "https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map",
                    {
                        "listing_status": status,
                        "start": start,
                        "limit": page_size,
                        "aux": "status",
                    },
                ).json()
                data = payload.get("data") or payload.get("Data") or []
                if not isinstance(data, list):
                    raise RuntimeError(f"unexpected CMC map payload type status={status}")
                pages += 1
                total_rows += len(data)
                for row in data:
                    symbol = str(row.get("symbol") or "").upper().strip()
                    if not re.fullmatch(r"[A-Z0-9]{1,20}", symbol):
                        continue
                    for value in (row.get("name"), row.get("slug")):
                        key = norm(value)
                        if key:
                            cmc_names.setdefault(key, set()).add(symbol)
                print(
                    f"CMC_MAP_{status}_PAGE={pages} START={start} ROWS={len(data)}",
                    flush=True,
                )
                if len(data) < page_size:
                    break
                start += len(data)
                if pages >= 100:
                    raise RuntimeError(f"CMC map pagination guard exceeded status={status}")
            print(f"CMC_MAP_{status}=PASS pages={pages} rows={total_rows}", flush=True)
        except Exception as exc:
            print(
                f"CMC_MAP_{status}=WARN {type(exc).__name__} pages={pages} rows={total_rows}",
                flush=True,
            )
    cc_names: dict[str, set[str]] = {}
    try:
        payload = get(session, "https://min-api.cryptocompare.com/data/all/coinlist", {"summary": "true"}).json()
        for symbol, row in (payload.get("Data") or {}).items():
            sym = str(symbol or "").upper().strip()
            for value in (row.get("CoinName"), row.get("FullName")):
                key = norm(value)
                if key and re.fullmatch(r"[A-Z0-9]{1,20}", sym):
                    cc_names.setdefault(key, set()).add(sym)
    except Exception as exc:
        print(f"CRYPTOCOMPARE_MAP=WARN {type(exc).__name__}", flush=True)
    print(f"CMC_NAME_OR_SLUG_KEYS={len(cmc_names)} CC_NAME_KEYS={len(cc_names)}", flush=True)
    return cmc_names, cc_names


def pseudo(name: str) -> str:
    return "U" + hashlib.sha256(norm(name).encode("utf-8")).hexdigest()[:8].upper()


def currency_link_slugs(html: str) -> dict[str, set[str]]:
    """Return normalized anchor-text -> historical CMC currency slugs.

    Only /currencies/<slug>/ links are admitted and consumers require a unique
    slug for the exact normalized historical name. Ambiguous anchor text is
    therefore never auto-resolved.
    """
    links: dict[str, set[str]] = {}
    try:
        root = lxml_html.fromstring(html)
    except Exception:
        return links
    for anchor in root.xpath("//a[@href]"):
        href = str(anchor.get("href") or "")
        match = re.search(r"(?:https?://[^/]+)?/currencies/([^/?#]+)/?", href, flags=re.IGNORECASE)
        if not match:
            continue
        slug = norm(match.group(1))
        text = norm(" ".join(str(x) for x in anchor.itertext()))
        if slug and text:
            links.setdefault(text, set()).add(slug)
    return links


def resolve_symbol(
    name: str,
    materialized: str,
    cmc_names: dict[str, set[str]],
    cc_names: dict[str, set[str]],
    cmc_slug: str = "",
) -> tuple[str, str]:
    direct = str(materialized or "").upper().strip()
    if re.fullmatch(r"[A-Z0-9]{1,20}", direct) and direct not in {"NAN", "NONE"}:
        return direct, "PAGE_MATERIALIZED"
    key = norm(name)
    alias = HISTORICAL_NAME_ALIASES.get(key)
    if alias:
        return alias, "CURATED_HISTORICAL_ALIAS"
    cmc = sorted(cmc_names.get(key, set()))
    if len(cmc) == 1:
        return cmc[0], "CMC_KEYLESS_NAME_MAP"
    slug_key = norm(cmc_slug)
    slug_matches = sorted(cmc_names.get(slug_key, set())) if slug_key else []
    if len(slug_matches) == 1:
        return slug_matches[0], "CMC_HISTORICAL_SLUG_MAP"
    cc = sorted(cc_names.get(key, set()))
    if len(cc) == 1:
        return cc[0], "CRYPTOCOMPARE_NAME_MAP"
    return pseudo(name), "UNRESOLVED_AUDIT_KEY"


def clean_materialized_name(name: str, symbol: str, resolution: str) -> str:
    """Remove the duplicated ticker prefix created by CMC's materialized cell.

    This is deliberately restricted to PAGE_MATERIALIZED rows, where the symbol
    comes from a separate authoritative table cell. Lazy rows are never guessed.
    """
    raw = str(name or "").strip()
    ticker = str(symbol or "").strip()
    if resolution == "PAGE_MATERIALIZED" and ticker and raw.upper().startswith(ticker.upper()) and len(raw) > len(ticker):
        remainder = raw[len(ticker):].strip()
        if remainder:
            return remainder
    return raw


def parse_page(html: str, day: pd.Timestamp, cmc_names: dict[str, set[str]], cc_names: dict[str, set[str]]) -> pd.DataFrame:
    tables = [flatten(t) for t in pd.read_html(StringIO(html))]
    candidates = []
    for table in tables:
        cols = list(table.columns)
        name_col, symbol_col = find(cols, "name"), find(cols, "symbol")
        rank_col, price_col = find(cols, "rank"), find(cols, "price")
        if name_col and symbol_col and rank_col and price_col and len(table) >= TOP_N:
            candidates.append(table)
    if not candidates:
        raise RuntimeError(f"CMC full ordered table unavailable {day.date()} tables={[len(t) for t in tables]}")
    table = max(candidates, key=len).reset_index(drop=True)
    cols = list(table.columns)
    name_col, symbol_col = find(cols, "name"), find(cols, "symbol")
    rank_col, price_col = find(cols, "rank"), find(cols, "price")
    mcap_col, volume_col = find(cols, "market cap"), find(cols, "volume")
    materialized_ranks = pd.to_numeric(table[rank_col], errors="coerce")
    known = materialized_ranks.notna()
    expected = pd.Series(np.arange(1, len(table) + 1), index=table.index, dtype=float)
    mismatch = int((materialized_ranks[known] != expected[known]).sum())
    if mismatch:
        raise RuntimeError(f"CMC ordered-table rank verification failed {day.date()} mismatches={mismatch}")
    page_slugs = currency_link_slugs(html)
    records = []
    for idx, row in table.iloc[:TOP_N].iterrows():
        raw_name = str(row[name_col] or "").strip()
        # Resolve the authoritative materialized ticker first so duplicated CMC
        # table text (e.g. FETFetch.ai) can be cleaned before slug lookup.
        symbol, resolution = resolve_symbol(raw_name, row[symbol_col], cmc_names, cc_names, "")
        name = clean_materialized_name(raw_name, symbol, resolution)
        slug_candidates = set(page_slugs.get(norm(raw_name), set()))
        slug_candidates.update(page_slugs.get(norm(name), set()))
        slug_candidates = sorted(slug_candidates)
        cmc_slug = slug_candidates[0] if len(slug_candidates) == 1 else ""
        # Lazy rows have no authoritative symbol cell; after recovering the
        # historical slug, give the identity maps one final fail-closed chance.
        if resolution != "PAGE_MATERIALIZED" and cmc_slug:
            symbol, resolution = resolve_symbol(raw_name, row[symbol_col], cmc_names, cc_names, cmc_slug)
            name = clean_materialized_name(raw_name, symbol, resolution)
        records.append({
            "snapshot_date": day.normalize(), "rank": idx + 1, "name": name, "symbol": symbol,
            "market_cap_usd": number(row[mcap_col]) if mcap_col else np.nan,
            "price_usd": number(row[price_col]),
            "volume_24h_usd": number(row[volume_col]) if volume_col else np.nan,
            "cmc_slug": cmc_slug,
            "symbol_resolution": resolution,
            "identity_resolved": resolution != "UNRESOLVED_AUDIT_KEY",
        })
    out = pd.DataFrame(records)
    if len(out) != TOP_N or out["rank"].nunique() != TOP_N:
        raise RuntimeError(f"CMC top150 reconstruction failed {day.date()} rows={len(out)}")
    return out


def reconcile_unique_historical_slugs(all_rows: pd.DataFrame) -> pd.DataFrame:
    """Reconcile lazy rows using a slug resolved unambiguously in another PIT page.

    CMC currency slugs are stronger identifiers than tickers. We use the full
    historical corpus only for identity lineage, never for features or trading
    information. A slug is backfilled only when every resolved occurrence in
    the corpus points to exactly one symbol. Ambiguous/reused slugs fail closed.
    """
    out = all_rows.copy()
    resolved = out[
        out["identity_resolved"].astype(bool)
        & out["cmc_slug"].fillna("").astype(str).map(bool)
    ].copy()
    slug_symbols = (
        resolved.groupby("cmc_slug")["symbol"]
        .agg(lambda values: sorted(set(str(v) for v in values if str(v))))
        .to_dict()
    )
    unique_map = {slug: symbols[0] for slug, symbols in slug_symbols.items() if len(symbols) == 1}
    mask = (~out["identity_resolved"].astype(bool)) & out["cmc_slug"].isin(unique_map)
    if mask.any():
        out.loc[mask, "symbol"] = out.loc[mask, "cmc_slug"].map(unique_map)
        out.loc[mask, "symbol_resolution"] = "CMC_CROSS_SNAPSHOT_SLUG_LINEAGE"
        out.loc[mask, "identity_resolved"] = True
    print(
        f"CMC_CROSS_SNAPSHOT_SLUG_LINEAGE={int(mask.sum())} UNIQUE_SLUGS={len(unique_map)}",
        flush=True,
    )
    return out


def collect_snapshots(session: requests.Session, outdir: Path) -> pd.DataFrame:
    cmc_names, cc_names = metadata_maps(session)
    dates = pd.date_range(START_SIGNAL, END_SIGNAL, freq="ME")
    rows = []
    for index, day in enumerate(dates, 1):
        url = f"https://coinmarketcap.com/historical/{day.strftime('%Y%m%d')}/"
        frame = parse_page(get(session, url).text, day, cmc_names, cc_names)
        frame["source_url"] = url
        rows.append(frame)
        counts = frame["symbol_resolution"].value_counts().to_dict()
        print(f"CMC {index}/{len(dates)} {day.date()} rows={len(frame)} resolution={counts}", flush=True)
        time.sleep(0.08)
    all_rows = reconcile_unique_historical_slugs(pd.concat(rows, ignore_index=True))
    all_rows.to_csv(outdir / "CMC_MONTH_END_TOP150.csv", index=False)
    unresolved = all_rows[~all_rows["identity_resolved"]][["snapshot_date","rank","name","symbol","cmc_slug"]]
    unresolved.to_csv(outdir / "CMC_UNRESOLVED_IDENTITIES.csv", index=False)
    if all_rows["snapshot_date"].nunique() != len(dates):
        raise RuntimeError("missing CMC month-end snapshots")
    return all_rows
