#!/usr/bin/env python3
"""Outcome-blind causal feature materialization for Grammar 007.

Reads BCB/CVM feature sources and the already-frozen availability authority only.
It does NOT download/parse B3 COTAHIST, returns, outcomes or economics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

UA = "QRDS-GATE-BTC-RESEARCH-ONLY/1.0"
TIMEOUT = 120
SCHEMA = "qrds.factory.grammar_007.causal_feature_materialization.v1"
BCB_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
CVM_INF = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{yyyymm}.zip"
CVM_DELIVERY_2024 = "https://dados.cvm.gov.br/dados/FI/DOC/ENTREGA/DADOS/HIST/fi_entrega_documento_2024.zip"
CVM_CAD_HIST = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi_hist.zip"
CVM_REGISTRY = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"

# CVM historical text fields can exceed Python's conservative CSV default.
# Raising the parser ceiling changes transport capacity only; it does not alter
# scientific eligibility, classification, or outcome boundaries.
csv.field_size_limit(16 * 1024 * 1024)

SAFETY = {
    "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
    "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
    "NO_BACKFILL": True, "NO_LATE_SEAL": True, "NO_COUNTER_RESET": True,
    "NO_RETUNE": True, "FAIL_CLOSED": True, "H1_H31_ISOLATED": True,
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm_cnpj(x: str | None) -> str:
    return re.sub(r"\D", "", x or "")


def dec(x: str | None) -> float | None:
    if x is None:
        return None
    s = x.strip().replace(".", "").replace(",", ".") if "," in x else x.strip()
    if not s:
        return None
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def parse_day(x: str | None) -> date | None:
    if not x:
        return None
    s = x.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def read_zip_csvs(data: bytes) -> list[tuple[str, list[str], list[dict[str, str]]]]:
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".csv", ".txt")):
                continue
            raw = zf.read(name)
            text = raw.decode("utf-8-sig", errors="replace")
            sample = text.splitlines()[0] if text.splitlines() else ""
            delimiter = ";" if sample.count(";") >= sample.count(",") else ","
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            out.append((name, reader.fieldnames or [], rows))
    return out


def bcb_query(indicator: str) -> str:
    filt = urllib.parse.quote(f"Indicador eq '{indicator}'", safe="")
    return f"{BCB_BASE}?$format=json&$top=10000&$filter={filt}"


def bcb_rows(indicator: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = get(bcb_query(indicator))
    obj = json.loads(raw.decode("utf-8"))
    rows = obj.get("value", [])
    bases = sorted({str(r.get("baseCalculo")) for r in rows})
    return rows, {"url": bcb_query(indicator), "sha256": sha256(raw), "row_count": len(rows), "baseCalculo_values": bases}


def select_focus_series(rows: list[dict[str, Any]], indicator: str, eligible_mondays: list[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[tuple[date, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        d = parse_day(str(r.get("Data") or ""))
        ref = str(r.get("DataReferencia") or "").strip()
        if d:
            grouped[(d, ref)].append(r)
    all_dates = sorted({k[0] for k in grouped})
    result = []
    reasons = defaultdict(int)
    prev_value: float | None = None
    prev_pub: str | None = None
    for pub_s in eligible_mondays:
        pub = date.fromisoformat(pub_s)
        candidates = [d for d in all_dates if d < pub]
        if not candidates:
            reasons["NO_PREPUBLICATION_BCB_DATE"] += 1
            continue
        d = candidates[-1]
        key = (d, str(pub.year))
        rr = grouped.get(key, [])
        if not rr:
            reasons["NO_CURRENT_YEAR_REFERENCE"] += 1
            continue
        values = sorted({dec(str(x.get("Mediana"))) for x in rr if dec(str(x.get("Mediana"))) is not None})
        if len(values) != 1:
            reasons["AMBIGUOUS_BASECALCULO_MEDIANA"] += 1
            continue
        value = values[0]
        if prev_value is None:
            reasons["NEEDS_PREVIOUS_PUBLICATION"] += 1
            prev_value, prev_pub = value, pub_s
            continue
        result.append({
            "family_id": "XAGRAMMAR_728DC88D691B",
            "indicator": indicator,
            "publication_date": pub_s,
            "source_observation_date": d.isoformat(),
            "data_reference": str(pub.year),
            "median": value,
            "previous_publication_date": prev_pub,
            "revision": value - prev_value,
            "causal_available_before_session": True,
        })
        prev_value, prev_pub = value, pub_s
    return result, dict(reasons)


def inspect_cad_history(data: bytes) -> tuple[dict[str, list[tuple[date | None, str]]], dict[str, Any]]:
    """Build only classifications directly evidenced by CVM historical class files."""
    by_cnpj: dict[str, list[tuple[date | None, str]]] = defaultdict(list)
    diagnostics = {"members": [], "candidate_members": [], "rows_examined": 0}
    for name, fields, rows in read_zip_csvs(data):
        diagnostics["members"].append({"name": name, "fields": fields, "rows": len(rows)})
        upper = {f.upper(): f for f in fields}
        cnpj_f = next((upper[k] for k in upper if "CNPJ" in k and "FUNDO" in k), None)
        class_f = next((upper[k] for k in upper if k in {"CLASSE", "CLASSIFICACAO", "CLASSIFICAÇÃO"} or "CLASSE" == k), None)
        date_f = next((upper[k] for k in upper if k in {"DT_INI_CLASSE", "DATA_INICIO", "DT_INI", "DT_REG"}), None)
        if not cnpj_f or not class_f:
            continue
        diagnostics["candidate_members"].append(name)
        for row in rows:
            diagnostics["rows_examined"] += 1
            cnpj = norm_cnpj(row.get(cnpj_f))
            cls = (row.get(class_f) or "").strip()
            if cnpj and cls:
                by_cnpj[cnpj].append((parse_day(row.get(date_f)) if date_f else None, cls))
    for cnpj in by_cnpj:
        by_cnpj[cnpj].sort(key=lambda x: x[0] or date.min)
    diagnostics["classified_cnpj_count"] = len(by_cnpj)
    return by_cnpj, diagnostics


def equity_at(history: dict[str, list[tuple[date | None, str]]], cnpj: str, d: date) -> bool | None:
    vals = history.get(cnpj)
    if not vals:
        return None
    eligible = [x for x in vals if x[0] is None or x[0] <= d]
    if not eligible:
        return None
    cls = eligible[-1][1].upper()
    return "AÇ" in cls or "ACO" in cls or "AÇ" in cls


def parse_inf_month(data: bytes) -> list[dict[str, str]]:
    files = read_zip_csvs(data)
    rows: list[dict[str, str]] = []
    for _, fields, rr in files:
        if any(f in fields for f in ("DT_COMPTC",)):
            rows.extend(rr)
    return rows


def cvm_feature_rows(authority: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cad_raw = get(CVM_CAD_HIST)
    hist, hist_diag = inspect_cad_history(cad_raw)
    delivery_raw = get(CVM_DELIVERY_2024)
    delivery_files = read_zip_csvs(delivery_raw)
    delivery: dict[tuple[str, date], list[datetime]] = defaultdict(list)
    for _, fields, rows in delivery_files:
        if "Data_Hora_Entrega" not in fields:
            continue
        for r in rows:
            cnpj = norm_cnpj(r.get("CNPJ_Fundo_Classe"))
            comp = parse_day(r.get("Data_Fim_Competencia") or r.get("Data_Inicio_Competencia"))
            stamp = (r.get("Data_Hora_Entrega") or "").strip()
            if not cnpj or not comp or not stamp:
                continue
            try:
                dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=-3)))
                delivery[(cnpj, comp)].append(dt)
            except ValueError:
                continue

    sessions = [x for x in authority["B3"]["sessions"] if "2024-02-05" <= x["date"] <= "2024-09-30"]
    monthly: dict[str, list[dict[str, str]]] = {}
    source_hashes = {"cad_fi_hist": sha256(cad_raw), "delivery_2024": sha256(delivery_raw)}
    for ym in sorted({x["date"][:7].replace("-", "") for x in sessions}):
        raw = get(CVM_INF.format(yyyymm=ym))
        monthly[ym] = parse_inf_month(raw)
        source_hashes[f"inf_{ym}"] = sha256(raw)

    daily_by_date: dict[date, list[dict[str, str]]] = defaultdict(list)
    for rows in monthly.values():
        for r in rows:
            d = parse_day(r.get("DT_COMPTC"))
            if d:
                daily_by_date[d].append(r)

    features = []
    reasons = defaultdict(int)
    prev_nav: float | None = None
    prev_report_date: date | None = None
    for sess in sessions:
        sd = date.fromisoformat(sess["date"])
        open_dt = datetime.combine(sd, datetime.strptime(sess["open"], "%H:%M").time(), tzinfo=timezone(timedelta(hours=-3)))
        eligible_dates = []
        for comp, rows in daily_by_date.items():
            if comp >= sd:
                continue
            any_causal = False
            for r in rows:
                cnpj = norm_cnpj(r.get("CNPJ_FUNDO_CLASSE") or r.get("CNPJ_FUNDO"))
                stamps = delivery.get((cnpj, comp), [])
                if any(ts < open_dt for ts in stamps):
                    any_causal = True
                    break
            if any_causal:
                eligible_dates.append(comp)
        if not eligible_dates:
            reasons["NO_CAUSALLY_DELIVERED_REPORT_DATE"] += 1
            continue
        comp = max(eligible_dates)
        subs = reds = nav = 0.0
        count = 0
        unknown_class = 0
        for r in daily_by_date[comp]:
            cnpj = norm_cnpj(r.get("CNPJ_FUNDO_CLASSE") or r.get("CNPJ_FUNDO"))
            stamps = delivery.get((cnpj, comp), [])
            if not any(ts < open_dt for ts in stamps):
                continue
            eq = equity_at(hist, cnpj, comp)
            if eq is None:
                unknown_class += 1
                continue
            if not eq:
                continue
            a, b, c = dec(r.get("CAPTC_DIA")), dec(r.get("RESG_DIA")), dec(r.get("VL_PATRIM_LIQ"))
            if a is None or b is None or c is None:
                continue
            subs += a
            reds += b
            nav += c
            count += 1
        if count == 0:
            reasons["NO_EQUITY_FUNDS_WITH_CAUSAL_CLASSIFICATION"] += 1
            continue
        if prev_nav is None or prev_report_date is None:
            prev_nav, prev_report_date = nav, comp
            reasons["NEEDS_PRIOR_AGGREGATE_NAV"] += 1
            continue
        if prev_nav <= 0:
            reasons["NONPOSITIVE_PRIOR_AGGREGATE_NAV"] += 1
            prev_nav, prev_report_date = nav, comp
            continue
        features.append({
            "family_id": "XAGRAMMAR_62943307741A",
            "target_session_date": sess["date"],
            "target_session_open": sess["open"],
            "source_report_date": comp.isoformat(),
            "prior_report_date": prev_report_date.isoformat(),
            "equity_fund_count": count,
            "unknown_classification_count": unknown_class,
            "aggregate_subscriptions": subs,
            "aggregate_redemptions": reds,
            "prior_aggregate_nav": prev_nav,
            "EQUITY_FUND_AGG_NET_FLOW_OVER_PRIOR_AGG_NAV": (subs - reds) / prev_nav,
            "causal_available_before_session": True,
        })
        prev_nav, prev_report_date = nav, comp
    diag = {
        "coverage_start": "2024-02-05", "coverage_end": "2024-09-30",
        "post_rcvm175_dates_ineligible": True,
        "post_rcvm175_reason": "HISTORICAL_CLASS_VERSIONING_NOT_YET_PROVEN_FOR_REGISTRO_CLASSE",
        "classification_history": hist_diag,
        "source_hashes": source_hashes,
        "ineligible_reasons": dict(reasons),
    }
    return features, diag


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    authority = json.loads(args.authority.read_text(encoding="utf-8"))
    assert authority["status"] == "BOUNDED_PIT_AUTHORITIES_MATERIALIZED"

    eligible_mondays = [x["publication_date"] for x in authority["BCB"]["eligible_monday_publications"]]
    ipca_raw, ipca_meta = bcb_rows("IPCA")
    selic_raw, selic_meta = bcb_rows("Selic")
    ipca_rows, ipca_reasons = select_focus_series(ipca_raw, "IPCA", eligible_mondays)
    selic_rows, selic_reasons = select_focus_series(selic_raw, "Selic", eligible_mondays)

    by_pub_ipca = {x["publication_date"]: x for x in ipca_rows}
    by_pub_selic = {x["publication_date"]: x for x in selic_rows}
    focus_features = []
    for pub in sorted(set(by_pub_ipca) & set(by_pub_selic)):
        i, s = by_pub_ipca[pub], by_pub_selic[pub]
        focus_features.append({
            "family_id": "XAGRAMMAR_728DC88D691B",
            "publication_date": pub,
            "target_session_date": pub,
            "source_observation_date_ipca": i["source_observation_date"],
            "source_observation_date_selic": s["source_observation_date"],
            "IPCA_CURRENT_YEAR_MEDIAN_REVISION": i["revision"],
            "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION": s["revision"],
            "causal_available_before_session": True,
        })

    cvm_features, cvm_diag = cvm_feature_rows(authority)

    result = {
        "schema": SCHEMA,
        "materialized_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "CAUSAL_FEATURE_MATERIALIZATION_OUTCOME_BLIND",
        "status": "FEATURES_MATERIALIZED_OUTCOME_BLIND" if focus_features and cvm_features else "FEATURE_MATERIALIZATION_PARTIAL_FAIL_CLOSED",
        "families": {
            "XAGRAMMAR_728DC88D691B": {
                "feature_names": ["IPCA_CURRENT_YEAR_MEDIAN_REVISION", "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION"],
                "row_count": len(focus_features), "rows": focus_features,
                "source_meta": {"IPCA": ipca_meta, "Selic": selic_meta},
                "ineligible_reasons": {"IPCA": ipca_reasons, "Selic": selic_reasons},
            },
            "XAGRAMMAR_62943307741A": {
                "feature_names": ["EQUITY_FUND_AGG_NET_FLOW_OVER_PRIOR_AGG_NAV"],
                "row_count": len(cvm_features), "rows": cvm_features, "diagnostics": cvm_diag,
            },
        },
        "candidate_universe_frozen": False,
        "validation_started": False,
        "historical_testing_started": False,
        "candidate_ranked": False,
        "target_source_opened": False,
        "target_bytes_read": False,
        "outcomes_read": False,
        "economics_read": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "next_gate": "FREEZE_CANDIDATE_UNIVERSE_BEFORE_TARGET_READ",
        "safety": SAFETY,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "focus_rows": len(focus_features), "cvm_rows": len(cvm_features),
        "target_bytes_read": False, "outcomes_read": False, "next_gate": result["next_gate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())