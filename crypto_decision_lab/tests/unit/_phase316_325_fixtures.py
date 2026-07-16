from __future__ import annotations
import csv, gzip, json, hashlib
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import LOCKS
from crypto_decision_lab.scripts.phase303_finite_hypothesis_registry_v2_research_only import registry


def payload(phase:int, **fields:Any)->dict[str,Any]:
    value={"phase":phase,"project":"QRDS/QOS/GATE BTC","status":f"PHASE_{phase}_TEST","descriptive_only":True,"valid_for_decision":False,"approval_effect":"NONE_RESEARCH_ONLY","historical_result_authorizes_execution":False,"locks":dict(LOCKS),"gate":f"PHASE{phase}_TEST_GATE_RESEARCH_ONLY","artifact_fingerprint":f"fingerprint-{phase}"}
    value.update(fields); return value

def write_json(path:Path,value:dict[str,Any])->Path:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8"); return path

def patch_roots(monkeypatch,root:Path,*modules:Any)->None:
    import crypto_decision_lab.scripts.phase316_325_negative_evidence_common as common
    monkeypatch.setattr(common,"ROOT",root)
    for module in modules: monkeypatch.setattr(module,"ROOT",root)

def _write_gz(path:Path,fields:list[str],rows:list[dict[str,Any]])->dict[str,Any]:
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    raw=path.read_bytes(); stamps=[]
    for row in rows:
        for key in ("open_time_ms","funding_time_ms","timestamp_ms"):
            if key in row: stamps.append(int(row[key])); break
    return {"name":path.stem.replace('.csv',''),"path":path.as_posix(),"sha256":hashlib.sha256(raw).hexdigest(),"rows":len(rows),"start_ms":min(stamps),"end_ms":max(stamps),"quality":{"rows":len(rows),"duplicate_count":0,"gap_count":0,"missing_interval_count":0,"gaps_preview":[]}}

def phase301_fixture(root:Path,hours:int=800)->dict[str,Any]:
    base=1_700_000_000_000//3_600_000*3_600_000; datasets={}; providers=[("binance_candles",100.0),("bybit_candles",100.08),("okx_candles",99.96)]
    for name,offset in providers:
        rows=[]
        for i in range(hours):
            close=offset+i*0.01
            rows.append({"provider":name.split('_')[0].upper(),"market_type":"TEST","symbol":"BTCUSDT","interval":"1h","open_time_ms":base+i*3_600_000,"open_time_utc":"","open":close,"high":close*1.001,"low":close*0.999,"close":close,"volume":1000+i,"quote_volume":100000,"complete":True})
        rel=Path(f"artifacts/phase301/{name}.csv.gz"); rec=_write_gz(root/rel,["provider","market_type","symbol","interval","open_time_ms","open_time_utc","open","high","low","close","volume","quote_volume","complete"],rows); rec["path"]=rel.as_posix(); datasets[name]=rec
    funding=[]
    for i in range(100): funding.append({"provider":"BINANCE","market_type":"TEST","symbol":"BTCUSDT","funding_time_ms":base+i*8*3_600_000,"funding_time_utc":"","funding_rate":0.0001})
    rel=Path("artifacts/phase301/binance_funding.csv.gz"); rec=_write_gz(root/rel,["provider","market_type","symbol","funding_time_ms","funding_time_utc","funding_rate"],funding); rec["path"]=rel.as_posix(); datasets["binance_funding"]=rec
    oi=[]
    for i in range(hours): oi.append({"provider":"BYBIT","market_type":"TEST","symbol":"BTCUSDT","timestamp_ms":base+i*3_600_000,"timestamp_utc":"","open_interest":1_000_000+i})
    rel=Path("artifacts/phase301/bybit_open_interest.csv.gz"); rec=_write_gz(root/rel,["provider","market_type","symbol","timestamp_ms","timestamp_utc","open_interest"],oi); rec["path"]=rel.as_posix(); datasets["bybit_open_interest"]=rec
    return payload(301,datasets=datasets,successful_candle_providers=["BINANCE","BYBIT","OKX"],max_candle_rows=hours,minimum_two_candle_sources=True,complete=True,forward_evidence_credit=0,historical_backfill_to_forward_clock=False)

def phase303_fixture()->dict[str,Any]: return payload(303,experiment_budget=24,registered_hypotheses=24,registry_closed=True,hypotheses=registry())
def phase304_fixture()->dict[str,Any]: return payload(304,modal_hypothesis_id="OI_MOM_H8_T005",outer_metrics_10bps={"mean_per_10000_brl":-10.4,"lower_95_per_10000_brl":-18.19},strategy_approved=False,forward_shadow_eligible=False)
def phase311_fixture()->dict[str,Any]: return payload(311,candidate_hypothesis_id="OI_MOM_H8_T005",candidate_eligible=False,eligibility_gate_count=9,passed_gate_count=2,failed_gate_count=7,failed_gate_ids=["G01_SELECTION_STABILITY","G04_COST_ROBUSTNESS"])
def phase315_fixture()->dict[str,Any]: return payload(315,current_family_decision="CLOSE_CURRENT_FAMILY_RESEARCH_ONLY",candidate_eligible=False,strategy_approved=False)
def write_junit(path:Path,tests:int=10)->Path:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(f'<testsuite name="batch316_325" tests="{tests}" failures="0" errors="0" skipped="0"></testsuite>\n',encoding="utf-8"); return path
