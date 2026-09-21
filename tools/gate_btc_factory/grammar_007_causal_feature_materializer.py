#!/usr/bin/env python3
"""Outcome-blind causal feature materialization for Grammar 007.

Only feature-side official sources are read here. Target returns/economics remain
closed. A family that cannot be reconstructed point-in-time from versioned public
values is explicitly source-blocked instead of being approximated or backfilled.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

UA = "QRDS-GATE-BTC-RESEARCH-ONLY/1.0"
TIMEOUT = 60
SCHEMA = "qrds.factory.grammar_007.causal_feature_materialization.v2"
BCB_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
CVM_INF = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{yyyymm}.zip"
CVM_DELIVERY_DATASET = "https://dados.cvm.gov.br/dataset/fi-doc-entrega"
CVM_INF_DATASET = "https://dados.cvm.gov.br/dataset/fi-doc-inf_diario"
CVM_COVERAGE_END_PRE_TRANSITION = "2024-09-30"
CVM_POST_TRANSITION_BLOCKER = "HISTORICAL_CLASS_VERSIONING_NOT_YET_PROVEN_FOR_REGISTRO_CLASSE"
CVM_REVISION_VALUE_BLOCKER = "CVM_HISTORICAL_REPRESENTATION_VALUES_NOT_VERSIONED_BY_ID_DOCUMENTO_IN_STRUCTURED_OPEN_DATA"

SAFETY = {
    "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
    "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
    "NO_BACKFILL": True, "NO_LATE_SEAL": True, "NO_COUNTER_RESET": True,
    "NO_RETUNE": True, "FAIL_CLOSED": True, "H1_H31_ISOLATED": True,
}


def get_json(url: str) -> tuple[dict[str, Any], bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw.decode("utf-8")), raw


def dec(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(str(x).replace(",", "."))
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def parse_day(x: Any) -> date | None:
    if not x:
        return None
    s = str(x).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def bcb_query(indicator: str, start: str, end: str) -> str:
    # Bound the API read to the independently qualified authority window. OData
    # date filtering prevents $top=10000 from silently truncating to unrelated eras.
    filt = f"Indicador eq '{indicator}' and Data ge '{start}' and Data le '{end}'"
    encoded = urllib.parse.quote(filt, safe="")
    return f"{BCB_BASE}?$format=json&$top=10000&$filter={encoded}"


def bcb_rows(indicator: str, start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = bcb_query(indicator, start, end)
    obj, raw = get_json(url)
    rows = obj.get("value", [])
    return rows, {
        "url": url,
        "row_count": len(rows),
        "bounded_start": start,
        "bounded_end": end,
        "baseCalculo_values": sorted({str(r.get("baseCalculo")) for r in rows}),
        "payload_bytes": len(raw),
    }


def select_focus_series(
    rows: list[dict[str, Any]], indicator: str, eligible_mondays: list[str]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[tuple[date, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        d = parse_day(r.get("Data"))
        ref = str(r.get("DataReferencia") or "").strip()
        if d:
            grouped[(d, ref)].append(r)
    all_dates = sorted({k[0] for k in grouped})
    result: list[dict[str, Any]] = []
    reasons: defaultdict[str, int] = defaultdict(int)
    prev_value: float | None = None
    prev_pub: str | None = None
    prev_reference: str | None = None

    for pub_s in eligible_mondays:
        pub = date.fromisoformat(pub_s)
        candidates = [d for d in all_dates if d < pub]
        if not candidates:
            reasons["NO_PREPUBLICATION_BCB_DATE"] += 1
            continue
        source_day = candidates[-1]
        reference = str(pub.year)
        rr = grouped.get((source_day, reference), [])
        if not rr:
            reasons["NO_CURRENT_YEAR_REFERENCE"] += 1
            continue

        values = sorted({v for v in (dec(x.get("Mediana")) for x in rr) if v is not None})
        if len(values) != 1:
            reasons["AMBIGUOUS_BASECALCULO_MEDIANA"] += 1
            continue
        value = values[0]

        # Never compare different calendar-year horizons. The first eligible
        # publication of a new year establishes a new baseline and earns no row.
        if prev_value is None or prev_reference != reference:
            reasons["NEEDS_PREVIOUS_PUBLICATION_SAME_REFERENCE"] += 1
            prev_value, prev_pub, prev_reference = value, pub_s, reference
            continue

        result.append({
            "family_id": "XAGRAMMAR_728DC88D691B",
            "indicator": indicator,
            "publication_date": pub_s,
            "source_observation_date": source_day.isoformat(),
            "data_reference": reference,
            "median": value,
            "previous_publication_date": prev_pub,
            "revision": value - prev_value,
            "causal_available_before_session": True,
        })
        prev_value, prev_pub, prev_reference = value, pub_s, reference

    return result, dict(reasons)


def cvm_source_block() -> dict[str, Any]:
    """Terminal source qualification for the frozen CVM family.

    Delivery metadata contains Data_Hora_Entrega/ID_Documento and records later
    presentations, while the structured historical Informe Diario provides the
    consolidated row values rather than a value snapshot keyed by each historical
    ID_Documento. Therefore an old value as known before a later representation
    cannot be reconstructed from these structured public files without substituting
    today's revised value. That would be look-ahead, so the family remains zero-row.
    """
    return {
        "feature_names": ["EQUITY_FUND_AGG_NET_FLOW_OVER_PRIOR_AGG_NAV"],
        "row_count": 0,
        "rows": [],
        "status": "SOURCE_BLOCKED_NO_VERSIONED_PIT_VALUES",
        "blocker": CVM_REVISION_VALUE_BLOCKER,
        "coverage_attempted_through": CVM_COVERAGE_END_PRE_TRANSITION,
        "post_rcvm175_dates_ineligible": True,
        "post_rcvm175_reason": CVM_POST_TRANSITION_BLOCKER,
        "delivery_metadata_can_timestamp_presentations": True,
        "historical_structured_values_keyed_by_id_documento": False,
        "late_representation_value_substitution_allowed": False,
        "missing_rule": "INELIGIBLE_NO_IMPUTATION",
        "official_sources": [CVM_DELIVERY_DATASET, CVM_INF_DATASET],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    authority = json.loads(args.authority.read_text(encoding="utf-8"))
    assert authority["status"] == "BOUNDED_PIT_AUTHORITIES_MATERIALIZED"

    coverage_start = authority["coverage"]["start"]
    coverage_end = authority["coverage"]["end"]
    eligible_mondays = [x["publication_date"] for x in authority["BCB"]["eligible_monday_publications"]]

    ipca_raw, ipca_meta = bcb_rows("IPCA", coverage_start, coverage_end)
    selic_raw, selic_meta = bcb_rows("Selic", coverage_start, coverage_end)
    ipca_rows, ipca_reasons = select_focus_series(ipca_raw, "IPCA", eligible_mondays)
    selic_rows, selic_reasons = select_focus_series(selic_raw, "Selic", eligible_mondays)

    by_pub_ipca = {x["publication_date"]: x for x in ipca_rows}
    by_pub_selic = {x["publication_date"]: x for x in selic_rows}
    focus_features: list[dict[str, Any]] = []
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

    cvm = cvm_source_block()
    focus_ready = bool(focus_features)
    result = {
        "schema": SCHEMA,
        "materialized_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "CAUSAL_FEATURE_MATERIALIZATION_OUTCOME_BLIND",
        "status": "FOCUS_FEATURES_MATERIALIZED_CVM_SOURCE_BLOCKED" if focus_ready else "FEATURE_MATERIALIZATION_FAIL_CLOSED",
        "families": {
            "XAGRAMMAR_728DC88D691B": {
                "status": "FEATURES_MATERIALIZED_OUTCOME_BLIND" if focus_ready else "NO_CAUSAL_FEATURE_ROWS",
                "feature_names": ["IPCA_CURRENT_YEAR_MEDIAN_REVISION", "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION"],
                "row_count": len(focus_features),
                "rows": focus_features,
                "source_meta": {"IPCA": ipca_meta, "Selic": selic_meta},
                "ineligible_reasons": {"IPCA": ipca_reasons, "Selic": selic_reasons},
            },
            "XAGRAMMAR_62943307741A": cvm,
        },
        "terminal_source_blocked_families": ["XAGRAMMAR_62943307741A"],
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
        "next_gate": "FREEZE_CANDIDATE_UNIVERSE_BEFORE_TARGET_READ" if focus_ready else "SOURCE_REQUALIFICATION_REQUIRED",
        "safety": SAFETY,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "focus_rows": len(focus_features),
        "cvm_rows": 0,
        "cvm_blocker": CVM_REVISION_VALUE_BLOCKER,
        "target_bytes_read": False,
        "outcomes_read": False,
        "next_gate": result["next_gate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())