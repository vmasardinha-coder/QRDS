#!/usr/bin/env python3
"""Outcome-blind PIT semantics and target-source qualification for Grammar 007.

This gate does not materialize features, rank candidates, parse B3 target bytes,
or read outcomes/economics. It only qualifies timestamp/join/source semantics and
fails closed where historical point-in-time evidence is not independently proven.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.grammar_007.pit_source_qualification.v1"
UA = "QRDS-GATE-BTC-RESEARCH-ONLY/1.0"
TIMEOUT = 90

CVM_DELIVERY = "https://dados.cvm.gov.br/dados/FI/DOC/ENTREGA/DADOS/fi_entrega_documento_202609.zip"
B3_CALENDAR_2026 = "https://www.b3.com.br/main.jsp?lumA=1&lumII=8A80CB81633FBF0B0163402956733E3A&lumPageId=8A6882694E91F2D4014E9248DBB001C9"
B3_TRADING_HOURS = "https://www.b3.com.br/main.jsp?lumA=1&lumII=8A80CB81633FBF0B0163402B3B335F48&lumPageId=8A6882694E91F2D4014E9248DBB001D4"
B3_COTAHIST = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2025.ZIP"

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_LATE_SEAL": True,
    "NO_COUNTER_RESET": True,
    "NO_RETUNE": True,
    "FAIL_CLOSED": True,
    "H1_H31_ISOLATED": True,
}


def get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return {"url": url, "reachable": True, "http_status": int(r.status), "content_type": r.headers.get("Content-Type"), "body": body}
    except Exception as exc:
        return {"url": url, "reachable": False, "http_status": getattr(exc, "code", None), "error": f"{type(exc).__name__}:{exc}", "body": b""}


def head(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            length = r.headers.get("Content-Length")
            return {"url": url, "reachable": True, "http_status": int(r.status), "content_type": r.headers.get("Content-Type"),
                    "content_length": int(length) if length and length.isdigit() else None, "last_modified": r.headers.get("Last-Modified"),
                    "etag": r.headers.get("ETag"), "body_read": False}
    except Exception as exc:
        return {"url": url, "reachable": False, "http_status": getattr(exc, "code", None), "error": f"{type(exc).__name__}:{exc}", "body_read": False}


def public(rec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rec.items() if k != "body"}


def delivery_schema(rec: dict[str, Any]) -> dict[str, Any]:
    required = {"CNPJ_Fundo_Classe", "Tipo_Documento", "Data_Inicio_Competencia", "Data_Fim_Competencia", "ID_Documento", "Data_Hora_Entrega", "Tipo_Apresentacao", "Ativo"}
    if not rec.get("reachable"):
        return {"schema_pass": False, "required_fields": sorted(required), "observed_fields": [], "sample_rows_checked": 0}
    try:
        with zipfile.ZipFile(io.BytesIO(rec["body"])) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            observed: set[str] = set()
            samples = 0
            parseable_delivery_timestamps = 0
            for name in names:
                raw = zf.open(name)
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                reader = csv.DictReader(text, delimiter=";")
                observed.update(reader.fieldnames or [])
                for row in reader:
                    samples += 1
                    stamp = (row.get("Data_Hora_Entrega") or "").strip()
                    if stamp:
                        try:
                            datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                            parseable_delivery_timestamps += 1
                        except ValueError:
                            pass
                    if samples >= 50:
                        break
                if samples >= 50:
                    break
            return {"schema_pass": required.issubset(observed), "required_fields": sorted(required), "observed_fields": sorted(observed),
                    "sample_rows_checked": samples, "parseable_delivery_timestamps": parseable_delivery_timestamps,
                    "timestamp_parse_pass": samples > 0 and parseable_delivery_timestamps > 0}
    except Exception as exc:
        return {"schema_pass": False, "required_fields": sorted(required), "observed_fields": [], "sample_rows_checked": 0,
                "error": f"{type(exc).__name__}:{exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    cvm_raw = get(CVM_DELIVERY)
    cvm_shape = delivery_schema(cvm_raw)
    cvm_ready = bool(cvm_shape.get("schema_pass") and cvm_shape.get("timestamp_parse_pass"))

    calendar = head(B3_CALENDAR_2026)
    hours = head(B3_TRADING_HOURS)
    cotahist = head(B3_COTAHIST)
    b3_current_authority_reachable = bool(calendar.get("reachable") and hours.get("reachable") and cotahist.get("reachable"))

    bcb = {
        "official_release_day_semantics_documented": True,
        "historical_intraday_publication_timestamp_source_identified": False,
        "exact_historical_intraday_publication_timestamp_proven": False,
        "pit_admission_pass": False,
        "blocker": "BCB_FOCUS_HISTORICAL_INTRADAY_PUBLICATION_TIMESTAMP_NOT_INDEPENDENTLY_PROVEN",
        "status": "PIT_BLOCKED_TIMESTAMP_AUTHORITY_MISSING",
    }

    cvm = {
        "delivery_source": public(cvm_raw),
        "delivery_schema": cvm_shape,
        "join_contract": {
            "competency_keys": ["CNPJ_Fundo_Classe", "Data_Inicio_Competencia", "Data_Fim_Competencia", "Tipo_Documento"],
            "version_key": "ID_Documento",
            "availability_timestamp": "Data_Hora_Entrega",
            "presentation_type": "Tipo_Apresentacao",
            "active_flag": "Ativo",
            "rule": "For each fund/class competency, only a document version with Data_Hora_Entrega strictly before the target B3 regular-session open is eligible; later presentations/re-presentations roll prospectively and never overwrite prior PIT state.",
            "missing_rule": "INELIGIBLE_NO_IMPUTATION",
        },
        "join_contract_ready": cvm_ready,
        "pit_admission_pass": False,
        "status": "PIT_JOIN_CONTRACT_READY_NOT_EXECUTED" if cvm_ready else "PIT_JOIN_CONTRACT_BLOCKED_SCHEMA",
    }

    b3 = {
        "calendar_2026": calendar,
        "trading_hours": hours,
        "cotahist_target": cotahist,
        "current_authorities_reachable": b3_current_authority_reachable,
        "target_bytes_read": False,
        "target_bytes_parsed": False,
        "target_outcomes_read": False,
        "historical_session_calendar_versioning_proven": False,
        "historical_open_time_versioning_proven": False,
        "pit_admission_pass": False,
        "blocker": "B3_HISTORICAL_SESSION_AND_OPEN_TIME_VERSIONING_NOT_YET_MATERIALIZED",
        "status": "CURRENT_AUTHORITY_QUALIFIED_HISTORICAL_VERSIONING_PENDING" if b3_current_authority_reachable else "SOURCE_AUTHORITY_REACHABILITY_BLOCKED",
    }

    blockers = [bcb["blocker"], b3["blocker"]]
    if not cvm_ready:
        blockers.append("CVM_DELIVERY_JOIN_SCHEMA_NOT_QUALIFIED")

    result = {
        "schema": SCHEMA,
        "qualified_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "PIT_SEMANTICS_AND_TARGET_SOURCE_QUALIFICATION",
        "status": "PIT_SOURCE_QUALIFICATION_BLOCKED",
        "blockers": blockers,
        "BCB": bcb,
        "CVM": cvm,
        "B3": b3,
        "next_gate": "MATERIALIZE_HISTORICAL_AVAILABILITY_AUTHORITIES_WITHOUT_OUTCOMES",
        "historical_testing_started": False,
        "features_materialized": False,
        "candidate_ranked": False,
        "outcomes_read": False,
        "economics_read": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "safety": SAFETY,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "cvm_join_ready": cvm_ready, "b3_current_authority": b3_current_authority_reachable,
                      "bcb_pit": False, "outcomes_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
