#!/usr/bin/env python3
"""Fail-closed source QA for B3 H130-H139 sovereign-curve generation.

No economics are read or computed here. This script binds the official Tesouro
Transparente daily Tesouro Direto rates dataset, records provenance, validates
schema/date/title identity, and deterministically derives source-only curve nodes.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

PACKAGE_API = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
    "?id=taxas-dos-titulos-ofertados-pelo-tesouro-direto"
)
RESOURCE_ID = "796d2059-14e9-44e3-80c9-2d9e30b405c1"
EXPECTED_PACKAGE = "taxas-dos-titulos-ofertados-pelo-tesouro-direto"
CUTOFF_EXCLUSIVE = pd.Timestamp("2026-08-10")
OUT = Path("artifacts/b3_h130_h139/B3_H130_H139_SOURCE_QA.json")
NODE_OUT = Path("artifacts/b3_h130_h139/B3_H130_H139_CURVE_NODES.csv")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def get_json(url: str, attempts: int = 4) -> dict:
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=45, headers={"User-Agent": "QRDS-research-source-qa/1.0"})
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # fail closed after bounded retries
            last = exc
            time.sleep(2 ** i)
    raise RuntimeError(f"metadata fetch failed after {attempts} attempts: {last}")


def get_bytes(url: str, attempts: int = 4) -> tuple[bytes, str]:
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=120, headers={"User-Agent": "QRDS-research-source-qa/1.0"})
            r.raise_for_status()
            return r.content, r.headers.get("content-type", "")
        except Exception as exc:
            last = exc
            time.sleep(2 ** i)
    raise RuntimeError(f"resource fetch failed after {attempts} attempts: {last}")


def resolve_columns(columns: list[str]) -> dict[str, str]:
    by_norm = {norm(c): c for c in columns}
    required = {
        "title_type": "tipo titulo",
        "maturity": "data vencimento",
        "base_date": "data base",
        "buy_yield_morning": "taxa compra manha",
    }
    out = {}
    for key, expected in required.items():
        if expected not in by_norm:
            raise RuntimeError(f"required source column missing: {expected}; got={columns}")
        out[key] = by_norm[expected]
    return out


def select_node(g: pd.DataFrame, title_col: str, maturity_col: str, yield_col: str,
                exact_title: str, target_years: float) -> float | None:
    q = g[g[title_col] == exact_title].copy()
    if q.empty:
        return None
    q = q[q[yield_col].notna() & q[maturity_col].notna()]
    if q.empty:
        return None
    base = q["__base_date"].iloc[0]
    q["__years"] = (q[maturity_col] - base).dt.days / 365.2425
    q = q[q["__years"] > 0]
    if q.empty:
        return None
    q["__distance"] = (q["__years"] - float(target_years)).abs()
    q = q.sort_values(["__distance", maturity_col, title_col], kind="mergesort")
    return float(q.iloc[0][yield_col])


def main() -> None:
    meta = get_json(PACKAGE_API)
    if meta.get("success") is not True:
        raise RuntimeError("CKAN package_show did not return success=true")
    pkg = meta["result"]
    if pkg.get("name") != EXPECTED_PACKAGE:
        raise RuntimeError(f"package identity mismatch: {pkg.get('name')}")

    license_title = str(pkg.get("license_title") or "")
    if "odbl" not in norm(license_title) and "open data commons" not in norm(license_title):
        raise RuntimeError(f"unexpected/open-license identity not proven: {license_title}")

    resources = {r.get("id"): r for r in pkg.get("resources", [])}
    if RESOURCE_ID not in resources:
        raise RuntimeError(f"frozen resource id missing: {RESOURCE_ID}")
    res = resources[RESOURCE_ID]
    url = res.get("url")
    if not url or not str(url).lower().startswith("https://"):
        raise RuntimeError("frozen resource has no HTTPS URL")

    raw, content_type = get_bytes(url)
    if len(raw) < 100_000:
        raise RuntimeError(f"resource unexpectedly small: {len(raw)} bytes")

    parse_error = None
    df = None
    chosen_encoding = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=";", decimal=",", encoding=enc, low_memory=False)
            chosen_encoding = enc
            break
        except Exception as exc:
            parse_error = exc
    if df is None:
        raise RuntimeError(f"CSV parse failed: {parse_error}")

    df.columns = [str(c).strip() for c in df.columns]
    cols = resolve_columns(list(df.columns))
    title_col = cols["title_type"]
    maturity_col = cols["maturity"]
    base_col = cols["base_date"]
    yield_col = cols["buy_yield_morning"]

    df[title_col] = df[title_col].astype(str).str.strip()
    df["__base_date"] = pd.to_datetime(df[base_col], dayfirst=True, errors="coerce").dt.normalize()
    df[maturity_col] = pd.to_datetime(df[maturity_col], dayfirst=True, errors="coerce").dt.normalize()
    df[yield_col] = pd.to_numeric(df[yield_col], errors="coerce")
    if df["__base_date"].isna().any():
        raise RuntimeError("unparseable Data Base values present")

    key_dupes = int(df.duplicated([title_col, maturity_col, "__base_date"]).sum())
    if key_dupes:
        raise RuntimeError(f"duplicate title/maturity/base-date keys: {key_dupes}")

    exact_classes = sorted(set(df[title_col].dropna().astype(str)))
    required_classes = {"Tesouro Prefixado", "Tesouro IPCA+"}
    missing_classes = sorted(required_classes - set(exact_classes))
    if missing_classes:
        raise RuntimeError(f"exact title classes absent: {missing_classes}")

    hist = df[(df["__base_date"] >= pd.Timestamp("2020-01-01")) & (df["__base_date"] < CUTOFF_EXCLUSIVE)].copy()
    if hist.empty:
        raise RuntimeError("no 2020+ pre-cutoff history")

    nodes = []
    for d, g in hist.groupby("__base_date", sort=True):
        nodes.append({
            "date": d.date().isoformat(),
            "nominal2Y": select_node(g, title_col, maturity_col, yield_col, "Tesouro Prefixado", 2.0),
            "nominal5Y": select_node(g, title_col, maturity_col, yield_col, "Tesouro Prefixado", 5.0),
            "nominal8Y": select_node(g, title_col, maturity_col, yield_col, "Tesouro Prefixado", 8.0),
            "real5Y": select_node(g, title_col, maturity_col, yield_col, "Tesouro IPCA+", 5.0),
            "real10Y": select_node(g, title_col, maturity_col, yield_col, "Tesouro IPCA+", 10.0),
        })
    ndf = pd.DataFrame(nodes).sort_values("date").reset_index(drop=True)
    if ndf["date"].duplicated().any():
        raise RuntimeError("derived node dates are not unique")

    node_cols = ["nominal2Y", "nominal5Y", "nominal8Y", "real5Y", "real10Y"]
    coverage = {c: float(ndf[c].notna().mean()) for c in node_cols}
    per_year = {}
    years = pd.to_datetime(ndf["date"]).dt.year
    for y in range(2020, 2027):
        mask = years == y
        per_year[str(y)] = {
            "source_dates": int(mask.sum()),
            "node_nonnull": {c: int(ndf.loc[mask, c].notna().sum()) for c in node_cols},
        }

    NODE_OUT.parent.mkdir(parents=True, exist_ok=True)
    ndf.to_csv(NODE_OUT, index=False, lineterminator="\n")
    node_bytes = NODE_OUT.read_bytes()

    result = {
        "schema": "qrds.b3.h130_h139.source_qa.v1",
        "status": "SOURCE_QA_READY_STRATIFIED" if min(coverage.values()) >= 0.90 else "SOURCE_QA_NODE_COVERAGE_GAP",
        "provider": "Secretaria do Tesouro Nacional / Tesouro Transparente",
        "package_api": PACKAGE_API,
        "package_id": pkg.get("id"),
        "package_name": pkg.get("name"),
        "resource_id": RESOURCE_ID,
        "resource_url": url,
        "resource_format": res.get("format"),
        "license_title": license_title,
        "license_id": pkg.get("license_id"),
        "raw_sha256": sha256(raw),
        "raw_bytes": len(raw),
        "content_type": content_type,
        "csv_encoding": chosen_encoding,
        "csv_delimiter": ";",
        "csv_decimal": ",",
        "columns": list(df.columns),
        "resolved_columns": cols,
        "rows_total": int(len(df)),
        "duplicate_title_maturity_base_keys": key_dupes,
        "source_first_date": df["__base_date"].min().date().isoformat(),
        "source_last_date": df["__base_date"].max().date().isoformat(),
        "precutoff_2020plus_dates": int(ndf.shape[0]),
        "title_classes": exact_classes,
        "required_exact_title_classes": sorted(required_classes),
        "node_selection": {
            "nominal2Y": {"title_class": "Tesouro Prefixado", "target_years": 2.0},
            "nominal5Y": {"title_class": "Tesouro Prefixado", "target_years": 5.0},
            "nominal8Y": {"title_class": "Tesouro Prefixado", "target_years": 8.0},
            "real5Y": {"title_class": "Tesouro IPCA+", "target_years": 5.0},
            "real10Y": {"title_class": "Tesouro IPCA+", "target_years": 10.0},
            "tie_break": "abs maturity distance, then earlier maturity, then lexical title",
            "coupon_bearing_substitution": False,
        },
        "node_coverage_on_source_dates": coverage,
        "per_year": per_year,
        "derived_node_csv_sha256": sha256(node_bytes),
        "date_semantics": "Data Base is the provider reference date for the morning prices/yields; B3 joins must use only a completed Data Base strictly before the B3 signal session",
        "timezone_semantics": "daily source date; B3 join evaluated in America/Sao_Paulo with strict prior-date rule",
        "stale_limit_calendar_days": 5,
        "observed_fields": {
            "title_type": title_col,
            "maturity_date": maturity_col,
            "base_date": base_col,
            "morning_purchase_yield": yield_col,
        },
        "derived_fields": ["nominal2Y", "nominal5Y", "nominal8Y", "real5Y", "real10Y"],
        "cutoff_exclusive": "2026-08-10",
        "economics_run": False,
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "raw_sha256": result["raw_sha256"],
        "derived_node_csv_sha256": result["derived_node_csv_sha256"],
        "coverage": coverage,
        "dates": result["precutoff_2020plus_dates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
