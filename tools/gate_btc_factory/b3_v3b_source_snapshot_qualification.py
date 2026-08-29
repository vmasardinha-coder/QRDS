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

SOURCES = {
    "BCB_PTAX_FX": {
        "provider": "Banco Central do Brasil",
        "identifier": "PTAX-v1:CotacaoDolarPeriodo",
        "url": "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='01-01-2020'&@dataFinalCotacao='12-31-2024'&$format=json",
        "format": "json_ptax",
        "causal_policy": "REFERENCE_DATE_VALUE_USABLE_FROM_NEXT_B3_SESSION_ONLY",
        "publication_timing_status": "CONSERVATIVE_LAG_FROZEN",
    },
    "BCB_SELIC_1178": {
        "provider": "Banco Central do Brasil",
        "identifier": "SGS:1178",
        "url": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados?formato=json&dataInicial=01/01/2020&dataFinal=31/12/2024",
        "format": "json_sgs",
        "causal_policy": "NOT_AUTHORIZED_UNTIL_PUBLICATION_TIMING_PROVEN",
        "publication_timing_status": "UNRESOLVED",
    },
    "TESOURO_DIRETO_RATES": {
        "provider": "Tesouro Nacional",
        "identifier": "CKAN:796d2059-14e9-44e3-80c9-2d9e30b405c1",
        "url": "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv",
        "format": "csv_tesouro",
        "causal_policy": "NOT_AUTHORIZED_UNTIL_PUBLICATION_AND_REVISION_TIMING_PROVEN",
        "publication_timing_status": "UNRESOLVED",
    },
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-research-source-qualification/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def summarize_ptax(raw: bytes) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    rows = obj.get("value", [])
    dates = [str(r.get("dataHoraCotacao", ""))[:10] for r in rows if r.get("dataHoraCotacao")]
    fields = sorted({k for r in rows for k in r.keys()})
    return {"rows": len(rows), "first_date": min(dates) if dates else None, "last_date": max(dates) if dates else None, "fields": fields}


def summarize_sgs(raw: bytes) -> dict:
    rows = json.loads(raw.decode("utf-8"))
    dates = [r.get("data") for r in rows if r.get("data")]
    fields = sorted({k for r in rows for k in r.keys()})
    return {"rows": len(rows), "first_date": dates[0] if dates else None, "last_date": dates[-1] if dates else None, "fields": fields}


def summarize_tesouro(raw: bytes) -> dict:
    text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    fields = reader.fieldnames or []
    date_field = next((f for f in fields if "Data Base" in f or "Data" == f), None)
    dates = [r.get(date_field) for r in rows if date_field and r.get(date_field)]
    return {"rows": len(rows), "first_date": min(dates) if dates else None, "last_date": max(dates) if dates else None, "fields": fields}


def main() -> int:
    report = {
        "schema": "qrds.b3_autonomous_science.v3b.source_snapshot_qualification.v1",
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
            row["identity_history_status"] = "QUALIFIED_SNAPSHOT_IDENTITY_AND_COVERAGE"
        except Exception as exc:
            row["fetch_status"] = "FAIL_CLOSED"
            row["identity_history_status"] = "UNQUALIFIED"
            row["error"] = f"{type(exc).__name__}: {exc}"
            hard_fail = True
        report["sources"][name] = row

    # Stage B stays fail-closed until every selected source has causal publication/revision semantics proven.
    report["unresolved_gates"] = [
        name for name, row in report["sources"].items()
        if row.get("fetch_status") != "PASS" or row.get("publication_timing_status") == "UNRESOLVED"
    ]
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"hard_fail": hard_fail, "unresolved_gates": report["unresolved_gates"]}, sort_keys=True))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
