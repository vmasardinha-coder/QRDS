#!/usr/bin/env python3
"""Outcome-blind physical source capture for Grammar 007.

This stage proves only official feature-source reachability/schema/provenance and
records the official B3 COTAHIST target-source reachability state. It never parses
B3 target returns, never constructs a feature, and never reads economics.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.grammar_007.physical_source_capture.v1"
UA = "QRDS-GATE-BTC-RESEARCH-ONLY/1.0"
TIMEOUT = 90

BCB_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"
BCB_METADATA = f"{BCB_BASE}/$metadata"
BCB_ANNUAL = f"{BCB_BASE}/ExpectativasMercadoAnuais"

CVM_INF_META = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/META/meta_inf_diario_fi.txt"
CVM_INF_SAMPLE = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_202609.zip"
CVM_DELIVERY_META = "https://dados.cvm.gov.br/dados/FI/DOC/ENTREGA/META/meta_fi_entrega_documento.txt"
CVM_DELIVERY_SAMPLE = "https://dados.cvm.gov.br/dados/FI/DOC/ENTREGA/DADOS/fi_entrega_documento_202609.zip"
CVM_CLASS_REGISTRY = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
CVM_CLASS_META = "https://dados.cvm.gov.br/dados/FI/CAD/META/meta_registro_fundo_classe.zip"

B3_COTAHIST_CANDIDATES = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2025.ZIP",
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2024.ZIP",
)

SAFETY = {
    "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
    "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
    "NO_BACKFILL": True, "NO_LATE_SEAL": True, "NO_COUNTER_RESET": True,
    "NO_RETUNE": True, "FAIL_CLOSED": True, "H1_H31_ISOLATED": True,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return {"url": url, "reachable": True, "http_status": int(r.status),
                    "content_type": r.headers.get("Content-Type"), "last_modified": r.headers.get("Last-Modified"),
                    "etag": r.headers.get("ETag"), "byte_count": len(body), "sha256": sha256(body), "body": body}
    except urllib.error.HTTPError as exc:
        body = exc.read() if getattr(exc, "fp", None) else b""
        return {"url": url, "reachable": False, "http_status": int(exc.code), "error": f"HTTPError:{exc.code}",
                "byte_count": len(body), "sha256": sha256(body) if body else None, "body": body}
    except Exception as exc:
        return {"url": url, "reachable": False, "http_status": None, "error": f"{type(exc).__name__}:{exc}",
                "byte_count": 0, "sha256": None, "body": b""}


def head(url: str) -> dict[str, Any]:
    """Reachability/provenance probe only; never reads target response bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            length = r.headers.get("Content-Length")
            return {"url": url, "reachable": True, "http_status": int(r.status),
                    "content_type": r.headers.get("Content-Type"), "last_modified": r.headers.get("Last-Modified"),
                    "etag": r.headers.get("ETag"), "content_length": int(length) if length and length.isdigit() else None,
                    "body_read": False}
    except urllib.error.HTTPError as exc:
        return {"url": url, "reachable": False, "http_status": int(exc.code), "error": f"HTTPError:{exc.code}",
                "content_length": None, "body_read": False}
    except Exception as exc:
        return {"url": url, "reachable": False, "http_status": None, "error": f"{type(exc).__name__}:{exc}",
                "content_length": None, "body_read": False}


def public(rec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rec.items() if k != "body"}


def zip_schema(rec: dict[str, Any]) -> dict[str, Any]:
    if not rec.get("reachable"):
        return {"zip_valid": False, "members": [], "csv_headers": {}}
    try:
        with zipfile.ZipFile(io.BytesIO(rec["body"])) as zf:
            members = sorted(zf.namelist()); headers = {}
            for name in members:
                if name.lower().endswith((".csv", ".txt")):
                    text = zf.read(name)[:16384].decode("latin-1", errors="replace")
                    headers[name] = text.splitlines()[0] if text.splitlines() else ""
            return {"zip_valid": True, "members": members, "csv_headers": headers}
    except Exception as exc:
        return {"zip_valid": False, "members": [], "csv_headers": {}, "zip_error": f"{type(exc).__name__}:{exc}"}


def bcb_query(indicator: str) -> str:
    # Olinda's ExpectativasMercadoAnuais rejects $orderby on this endpoint (HTTP 400).
    # Physical capture needs only a schema-bearing official sample; chronology is
    # reconstructed later from Data under the frozen PIT gate, so no ordering is needed here.
    params = {"$format": "json", "$filter": f"Indicador eq '{indicator}'", "$top": "5"}
    return BCB_ANNUAL + "?" + urllib.parse.urlencode(params)


def parse_bcb(rec: dict[str, Any]) -> dict[str, Any]:
    if not rec.get("reachable"):
        return {"json_valid": False, "row_count": 0, "fields": []}
    try:
        rows = json.loads(rec["body"].decode("utf-8")).get("value", [])
        return {"json_valid": True, "row_count": len(rows), "fields": sorted({k for row in rows if isinstance(row, dict) for k in row})}
    except Exception as exc:
        return {"json_valid": False, "row_count": 0, "fields": [], "json_error": f"{type(exc).__name__}:{exc}"}


def meta_text_contains(rec: dict[str, Any], required: list[str]) -> dict[str, Any]:
    text = rec.get("body", b"").decode("latin-1", errors="replace")
    return {"required_tokens": required, "present": {x: x in text for x in required}}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); args = ap.parse_args()
    bcb_meta = get(BCB_METADATA); bcb_ipca = get(bcb_query("IPCA")); bcb_selic = get(bcb_query("Selic"))
    bcb_ipca_shape = parse_bcb(bcb_ipca); bcb_selic_shape = parse_bcb(bcb_selic)
    bcb_required = {"Indicador", "Data", "DataReferencia", "Mediana", "baseCalculo"}
    bcb_fields = set(bcb_ipca_shape["fields"]) | set(bcb_selic_shape["fields"])
    bcb_capture_pass = (bcb_meta.get("reachable") is True and bcb_ipca_shape["json_valid"] and bcb_ipca_shape["row_count"] > 0
                        and bcb_selic_shape["json_valid"] and bcb_selic_shape["row_count"] > 0 and bcb_required.issubset(bcb_fields))

    cvm_inf_meta=get(CVM_INF_META); cvm_inf=get(CVM_INF_SAMPLE); cvm_delivery_meta=get(CVM_DELIVERY_META); cvm_delivery=get(CVM_DELIVERY_SAMPLE)
    cvm_class_meta=get(CVM_CLASS_META); cvm_class=get(CVM_CLASS_REGISTRY)
    inf_schema=zip_schema(cvm_inf); delivery_schema=zip_schema(cvm_delivery); class_schema=zip_schema(cvm_class); class_meta_schema=zip_schema(cvm_class_meta)
    inf_tokens=meta_text_contains(cvm_inf_meta,["DT_COMPTC","CAPTC_DIA","RESG_DIA","VL_PATRIM_LIQ"])
    delivery_tokens=meta_text_contains(cvm_delivery_meta,["DT_ENTREGA","DT_COMPTC"])
    cvm_capture_pass=(cvm_inf_meta.get("reachable") is True and cvm_delivery_meta.get("reachable") is True and inf_schema.get("zip_valid") is True
                      and delivery_schema.get("zip_valid") is True and class_schema.get("zip_valid") is True and class_meta_schema.get("zip_valid") is True
                      and all(inf_tokens["present"].values()))
    b3_attempts=[head(url) for url in B3_COTAHIST_CANDIDATES]
    b3_reachable=any(x.get("reachable") is True for x in b3_attempts)
    source_gate={
      "BCB_OLINDA_EXPECTATIVASMERCADOANUAIS":{"physical_capture_pass":bcb_capture_pass,"schema_pass":bcb_required.issubset(bcb_fields),"required_fields":sorted(bcb_required),"observed_fields":sorted(bcb_fields),"metadata":public(bcb_meta),"ipca_sample":{**public(bcb_ipca),**bcb_ipca_shape},"selic_sample":{**public(bcb_selic),**bcb_selic_shape},"official_publication_cadence_documented":True,"exact_historical_intraday_publication_timestamp_proven":False,"pit_admission_pass":False,"status":"PHYSICAL_CAPTURE_PASS_PIT_TIMESTAMP_STILL_UNPROVEN" if bcb_capture_pass else "PHYSICAL_CAPTURE_FAIL"},
      "CVM_FI_INF_DIARIO_PLUS_DELIVERY_AND_CLASS_REGISTRY":{"physical_capture_pass":cvm_capture_pass,"inf_diario_meta":public(cvm_inf_meta),"inf_diario_meta_tokens":inf_tokens,"inf_diario_sample":{**public(cvm_inf),**inf_schema},"delivery_meta":public(cvm_delivery_meta),"delivery_meta_tokens":delivery_tokens,"delivery_sample":{**public(cvm_delivery),**delivery_schema},"class_registry_meta":{**public(cvm_class_meta),**class_meta_schema},"class_registry_sample":{**public(cvm_class),**class_schema},"revision_semantics_documented":True,"availability_mapping_requires_delivery_join":True,"pit_admission_pass":False,"status":"PHYSICAL_CAPTURE_PASS_PIT_JOIN_NOT_YET_MATERIALIZED" if cvm_capture_pass else "PHYSICAL_CAPTURE_FAIL"},
      "B3_COTAHIST_OFFICIAL":{"physical_capture_pass":b3_reachable,"attempts":[public(x) for x in b3_attempts],"target_bytes_read":False,"target_bytes_parsed":False,"target_outcomes_read":False,"pit_admission_pass":False,"status":"TARGET_PHYSICAL_CAPTURE_REACHABLE_UNPARSED" if b3_reachable else "TARGET_CAPTURE_FAIL"}}
    result={"schema":SCHEMA,"captured_at_utc":datetime.now(timezone.utc).isoformat(),"stage":"PHYSICAL_SOURCE_CAPTURE_ONLY",
            "status":"FEATURE_SOURCES_CAPTURED_TARGET_PENDING" if bcb_capture_pass and cvm_capture_pass and not b3_reachable else ("PHYSICAL_SOURCES_CAPTURED_NO_OUTCOME_READ" if bcb_capture_pass and cvm_capture_pass and b3_reachable else "SOURCE_CAPTURE_FAIL_CLOSED"),
            "sources":source_gate,"next_gate":"PIT_SEMANTICS_AND_TARGET_SOURCE_QUALIFICATION","historical_testing_started":False,"features_materialized":False,"candidate_ranked":False,"outcomes_read":False,"economics_read":False,"scientific_credit":0,"prospective_credit":0,"historical_backfill_credit":0,"safety":SAFETY}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"bcb":bcb_capture_pass,"cvm":cvm_capture_pass,"b3":b3_reachable},sort_keys=True))
    return 0 if bcb_capture_pass and cvm_capture_pass else 2

if __name__ == "__main__":
    raise SystemExit(main())
