#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
import requests

BASE="https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
CUTOFF=pd.Timestamp("2026-08-10")
OUT=Path("artifacts/b3_h140_h149/B3_H140_H149_SOURCE_QA.json")
CSV=Path("artifacts/b3_h140_h149/B3_H140_H149_PTAX_BULLETINS.csv")
REQ=("cotacaoCompra","cotacaoVenda","dataHoraCotacao")

def get_year(y:int):
    end=f"12-31-{y}" if y<2026 else "08-09-2026"
    params={"@dataInicial":f"'01-01-{y}'","@dataFinalCotacao":f"'{end}'","$format":"json"}
    url=BASE+"?"+urlencode(params,safe="'@$,")
    errs=[]
    for i in range(4):
        try:
            r=requests.get(url,timeout=90,headers={"User-Agent":"QRDS-B3-H140-source-qa/1.0"}); r.raise_for_status()
            raw=r.content; p=r.json(); rows=p.get("value")
            if not isinstance(rows,list): raise RuntimeError("NO_VALUE_LIST")
            return rows,{"year":y,"url":url,"http":r.status_code,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        except Exception as e:
            errs.append(type(e).__name__+":"+str(e)[:160]); time.sleep(2**i)
    raise RuntimeError(f"PTAX_FETCH_FAILED_{y}:{errs}")

def main():
    rows=[]; requests_meta=[]
    for y in range(2020,2027):
        q,m=get_year(y); rows.extend(q); requests_meta.append(m)
    if not rows: raise RuntimeError("NO_PTAX_ROWS")
    if any(not set(REQ).issubset(r) for r in rows): raise RuntimeError("PTAX_SCHEMA_MISMATCH")
    df=pd.DataFrame(rows)
    df["cotacaoCompra"]=pd.to_numeric(df["cotacaoCompra"],errors="coerce")
    df["cotacaoVenda"]=pd.to_numeric(df["cotacaoVenda"],errors="coerce")
    df["timestamp"]=pd.to_datetime(df["dataHoraCotacao"],errors="coerce")
    if df[list(REQ[:2])].isna().any().any() or df["timestamp"].isna().any(): raise RuntimeError("PTAX_NULL_REQUIRED")
    df["date"]=df["timestamp"].dt.normalize()
    df=df[(df.date>=pd.Timestamp("2020-01-01"))&(df.date<CUTOFF)].copy()
    dup=int(df.duplicated(["timestamp"]).sum())
    if dup: raise RuntimeError(f"DUPLICATE_PTAX_TIMESTAMP:{dup}")
    df["mid"]=(df.cotacaoCompra+df.cotacaoVenda)/2
    df["spread_bp"]=(df.cotacaoVenda-df.cotacaoCompra)/df.mid*1e4
    counts=df.groupby("date").size()
    # PTAX closing is based on four dealer-consultation windows since 2011; the
    # endpoint may expose extra bulletin rows. We require at least four distinct
    # timestamps for bulletin-dependent families and preserve every observed row.
    complete=counts[counts>=4]
    by_year={str(y):{"days":int((df.date.dt.year==y).groupby(df.date).any().sum()),"days_ge4":int(((counts.index.year==y)&(counts>=4)).sum())} for y in range(2020,2027)}
    coverage=float(len(complete)/len(counts)) if len(counts) else 0.0
    CSV.parent.mkdir(parents=True,exist_ok=True)
    df[["date","timestamp","cotacaoCompra","cotacaoVenda","mid","spread_bp"]].sort_values("timestamp").to_csv(CSV,index=False,lineterminator="\n")
    result={
      "schema":"qrds.b3.h140_h149.source_qa.v1","status":"SOURCE_QA_READY_STRATIFIED" if coverage>=.90 else "SOURCE_QA_BULLETIN_COVERAGE_GAP",
      "provider":"Banco Central do Brasil / Departamento das Reservas Internacionais","system":"PTAX","service":"PTAX v1 OData","endpoint":BASE,
      "license":"Open Data Commons ODbL (catalog dataset)","cutoff_exclusive":"2026-08-10","required_fields":list(REQ),
      "rows":int(len(df)),"source_days":int(len(counts)),"days_with_at_least_4_bulletins":int(len(complete)),"bulletin_day_coverage":coverage,
      "duplicate_timestamps":dup,"first_timestamp":df.timestamp.min().isoformat(),"last_timestamp":df.timestamp.max().isoformat(),"per_year":by_year,
      "request_manifest":requests_meta,"derived_csv_sha256":hashlib.sha256(CSV.read_bytes()).hexdigest(),
      "date_semantics":"dataHoraCotacao is an observed PTAX quote/bulletin timestamp; research joins must use only a completed PTAX calendar date strictly before B3 signal session",
      "timezone_semantics":"provider timestamp preserved as delivered; session eligibility interpreted in America/Sao_Paulo and forbids same-day conditioning",
      "dedupe_rule":"exact timestamp unique; no synthetic/missing bulletin fill","observed_fields":list(REQ),"derived_fields":["mid","spread_bp","daily fixing range","first-last drift","late-early drift","bulletin dispersion"],
      "economics_run":False,"h1_economics_read":False,"survivor_partial_economics_read":False,"orders":0,"real_capital":0,"engine_feed":False,"not_approved":True
    }
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("status","rows","source_days","days_with_at_least_4_bulletins","bulletin_day_coverage")},sort_keys=True))

if __name__=="__main__": main()
