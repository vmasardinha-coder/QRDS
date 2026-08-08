#!/usr/bin/env python3
"""Robust parser for CoinMarketCap historical ranking pages used by GATE BTC PIT audit."""
from __future__ import annotations

import re
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if isinstance(out.columns, pd.MultiIndex):
        columns = []
        for col in out.columns:
            parts = [str(x).strip() for x in col if str(x).strip() and not str(x).startswith("Unnamed")]
            columns.append(" ".join(dict.fromkeys(parts)))
        out.columns = columns
    else:
        out.columns = [str(c).strip() for c in out.columns]
    return out


def _find(columns: list[str], needle: str) -> str | None:
    needle = needle.lower()
    return next((col for col in columns if needle in col.lower()), None)


def _number(value: Any) -> float:
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


def parse_cmc_html(html: str, snapshot_date: pd.Timestamp, top_n: int = 150) -> pd.DataFrame:
    """Choose the table with the largest valid rank population, never first-match."""
    tables = pd.read_html(StringIO(html))
    candidates: list[tuple[int, int, pd.DataFrame, dict[str, str | None]]] = []
    diagnostics: list[str] = []
    for index, raw in enumerate(tables):
        table = _flatten_columns(raw)
        cols = list(table.columns)
        mapping = {
            "rank": _find(cols, "rank"),
            "name": _find(cols, "name"),
            "symbol": _find(cols, "symbol"),
            "market_cap": _find(cols, "market cap"),
            "price": _find(cols, "price"),
            "volume": _find(cols, "volume"),
        }
        if not mapping["rank"] or not mapping["symbol"] or not mapping["price"]:
            diagnostics.append(f"table={index} rows={len(table)} cols={cols[:12]} required_headers=false")
            continue
        ranks = pd.to_numeric(table[mapping["rank"]], errors="coerce")
        valid_rank_count = int(((ranks >= 1) & (ranks <= top_n)).sum())
        symbol_nonblank = int(table[mapping["symbol"]].astype(str).str.strip().ne("").sum())
        diagnostics.append(
            f"table={index} rows={len(table)} valid_ranks={valid_rank_count} symbol_nonblank={symbol_nonblank} cols={cols[:12]}"
        )
        candidates.append((valid_rank_count, symbol_nonblank, table, mapping))
    if not candidates:
        raise RuntimeError("CMC no candidate ranking table; " + " || ".join(diagnostics))
    candidates.sort(key=lambda item: (item[0], item[1], len(item[2])), reverse=True)
    score, _, chosen, mapping = candidates[0]
    if score < min(140, top_n):
        raise RuntimeError(
            f"CMC snapshot too short: {snapshot_date.date()} best_valid_ranks={score}; " + " || ".join(diagnostics)
        )
    rank_col = mapping["rank"]
    name_col = mapping["name"]
    symbol_col = mapping["symbol"]
    price_col = mapping["price"]
    if not all([rank_col, name_col, symbol_col, price_col]):
        raise RuntimeError(f"CMC required output columns missing for {snapshot_date.date()}: {mapping}")
    rank_values = pd.to_numeric(chosen[rank_col], errors="coerce")
    out = pd.DataFrame(index=chosen.index)
    out["snapshot_date"] = snapshot_date.normalize()
    out["rank"] = rank_values
    out["name"] = chosen[name_col].astype(str).str.strip()
    out["symbol"] = chosen[symbol_col].astype(str).str.upper().str.strip()
    out["market_cap_usd"] = chosen[mapping["market_cap"]].map(_number) if mapping["market_cap"] else np.nan
    out["price_usd"] = chosen[price_col].map(_number)
    out["volume_24h_usd"] = chosen[mapping["volume"]].map(_number) if mapping["volume"] else np.nan
    out = out[(out["rank"] >= 1) & (out["rank"] <= top_n)].copy()
    out["rank"] = out["rank"].astype(int)
    out = out[out["symbol"].str.fullmatch(r"[A-Z0-9]{1,20}", na=False)]
    out = out.sort_values("rank").drop_duplicates(["rank"], keep="first")
    if len(out) < min(140, top_n):
        raise RuntimeError(
            f"CMC filtered snapshot too short: {snapshot_date.date()} rows={len(out)} prefilter_valid_ranks={score}"
        )
    return out
