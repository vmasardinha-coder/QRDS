#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/gate_btc_factory/B3_V3B_SOURCE_QUALIFICATION_RUNTIME.json"
START = "2020-01-01"
END = "2024-12-31"
START_DT = datetime.strptime(START, "%Y-%m-%d").date()
END_DT = datetime.strptime(END, "%Y-%m-%d").date()

SOURCES = {
    "BCB_PTAX_FX": {
        "provider": "Banco Central do Brasil",
        "identifier": "PTAX-v1:CotacaoDolarPeriodo",
        "url": "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='01-01-2020'&@dataFinalCotacao='12-31-2024'&$format=json",
        "format": "json_ptax",
        "causal_policy": "REFERENCE_DATE_VALUE_USABLE_FROM_NEXT_B3_SESSION_ONLY",
        "publication_timing_status": "CONSERVATIVE_LAG_FROZEN",
        "revision_timing_status": "UNRESOLVED_CURRENT_SNAPSHOT_MAY_BE_REVISED",
    },
    "BCB_SELIC_1178": {
        "provider": "Banco Central do Brasil",
        "identifier": "SGS:1178",
        "url": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados?formato=json&dataInicial=01/01/2020&dataFinal=31/12/2024",
        "format": "json_sgs",
        "causal_policy": "NOT_AUTHORIZED_UNTIL_PUBLICATION_TIMING_PROVEN",
        "publication_timing_status": "UNRESOLVED",
        "revision_timing_status": "UNRESOLVED_CURRENT_SNAPSHOT_MAY_BE_REVISED",
    },
    "TESOURO_DIRETO_RATES": {
        "provider": "Tesouro Nacional",
        "identifier": "CKAN:796d2059-14e9-44e3-80c9-2d9e30b405c1",
        "url": "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv",
        "format": "csv_tesouro",
        "causal_policy": "REFERENCE_DATE_VALUE_USABLE_FROM_SECOND_B3_SESSION_ONLY_UNTIL_REVISION_SEMANTICS_PROVEN",
        "publication_timing_status": "OFFICIAL_NEXT_BUSINESS_DAY_DISCLOSURE_CONSERVATIVE_FULL_SESSION_LAG_FROZEN",
        "revision_timing_status": "UNRESOLVED_CURRENT_SNAPSHOT_MAY_BE_REVISED",
        "publication_evidence": "Tesouro Transparente metadata: periodicidade diaria; tempestividade = divulgacao no primeiro dia util apos o fechamento do mercado secundario",
        "publication_evidence_url": "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/1a8eb2e3-4902-4a38-a1eb-6410f23d90de/download/Taxa.pdf",
    },
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-research-source-qualification/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def parse_date(value: str):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    if len(value) >= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def coverage_summary(dates: list) -> dict:
    parsed = sorted(d for d in dates if d is not None)
    if not parsed:
        return {
            "first_date": None,
            "last_date": None,
            "rows_in_required_window": 0,
            "coverage_2020_2024": "FAIL_CLOSED_NO_PARSEABLE_DATES",
        }
    in_window = [d for d in parsed if START_DT <= d <= END_DT]
    years = {d.year for d in in_window}
    coverage_ok = 2020 in years and 2024 in years
    return {
        "first_date": parsed[0].isoformat(),
        "last_date": parsed[-1].isoformat(),
        "rows_in_required_window": len(in_window),
        "coverage_2020_2024": "PASS" if coverage_ok else "FAIL_CLOSED_INCOMPLETE_WINDOW",
    }


def summarize_ptax(raw: bytes) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    rows = obj.get("value", [])
    dates = [parse_date(str(r.get("dataHoraCotacao", ""))) for r in rows if r.get("dataHoraCotacao")]
    fields = sorted({k for r in rows for k in r.keys()})
    return {"rows": len(rows), "fields": fields, **coverage_summary(dates)}


def summarize_sgs(raw: bytes) -> dict:
    rows = json.loads(raw.decode("utf-8"))
    dates = [parse_date(str(r.get("data", ""))) for r in rows if r.get("data")]
    fields = sorted({k for r in rows for k in r.keys()})
    return {"rows": len(rows), "fields": fields, **coverage_summary(dates)}


def summarize_tesouro(raw: bytes) -> dict:
    text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    fields = reader.fieldnames or []
    date_field = next((f for f in fields if "Data Base" in f or f == "Data"), None)
    dates = [parse_date(str(r.get(date_field, ""))) for r in rows if date_field and r.get(date_field)]
    return {"rows": len(rows), "fields": fields, "date_field": date_field, **coverage_summary(dates)}


def main() -> int:
    report = {
        "schema": "qrds.b3_autonomous_science.v3b.source_snapshot_qualification.v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window": {"start": START, "end": END},
        "stage": "SOURCE_QUALIFICATION_ONLY_NO_ECONOMICS",
        "sources": {},
        "stage_b_authorized": False,
        "economics_authorized": False,
        "family_ids_authorized": False,
        "h2890_plus_authorized": False,
        "mt5_role": "INDEPENDENT_SECONDARY_SOURCE_CROSS_VALIDATION_ONLY",
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "no_counter_reset": True,
            "fail_closed": True,
            "h1_economics_read": False,
        },
    }
    hard_fail = False
    for name, spec in SOURCES.items():
        row = {k: v for k, v in spec.items() if k != "format"}
        try:
            raw = fetch(spec["url"])
            row["sha256"] = hashlib.sha256(raw).hexdigest()
            row["bytes"] = len(raw)
            if spec["format"] == "json_ptax":
                row["snapshot"] = summarize_ptax(raw)
            elif spec["format"] == "json_sgs":
                row["snapshot"] = summarize_sgs(raw)
            else:
                row["snapshot"] = summarize_tesouro(raw)
            row["fetch_status"] = "PASS"
            if row["snapshot"].get("coverage_2020_2024") == "PASS":
                row["identity_history_status"] = "QUALIFIED_SNAPSHOT_IDENTITY_AND_COVERAGE"
            else:
                row["identity_history_status"] = "FAIL_CLOSED_COVERAGE"
                hard_fail = True
        except Exception as exc:
            row["fetch_status"] = "FAIL_CLOSED"
            row["identity_history_status"] = "UNQUALIFIED"
            row["error"] = f"{type(exc).__name__}: {exc}"
            hard_fail = True
        report["sources"][name] = row

    report["unresolved_gates"] = [
        name for name, row in report["sources"].items()
        if row.get("fetch_status") != "PASS"
        or row.get("identity_history_status") != "QUALIFIED_SNAPSHOT_IDENTITY_AND_COVERAGE"
        or row.get("publication_timing_status") == "UNRESOLVED"
        or not row.get("revision_timing_status")
        or str(row.get("revision_timing_status", "")).startswith("UNRESOLVED")
    ]
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"hard_fail": hard_fail, "unresolved_gates": report["unresolved_gates"]}, sort_keys=True))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
