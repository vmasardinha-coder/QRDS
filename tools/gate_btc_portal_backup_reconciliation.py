"""Read-only NAV reconciliation of exported Portal ledgers; never rewrites a backup."""
import argparse,hashlib,json,math
from pathlib import Path

def audit(path):
    raw=Path(path).read_bytes();backup=json.loads(raw)
    ledgers={k:v["registros"] for k,v in backup["dados"].items() if k.startswith("ledger_diario_") and isinstance(v,dict) and "registros" in v}
    report={"schema":"gate_btc.portal_backup_reconciliation.v1","backup_sha256":hashlib.sha256(raw).hexdigest(),
            "backup_generated_at":backup["geradoEm"],"source_rewritten":False,
            "daily_return_correction_candidates":[],"ledgers":[],
            "served_version_verified":False,"btc_price_provenance_verified":False,
            "actual_costs_verified":False,"scientific_credit":0}
    for key,rows in sorted(ledgers.items()):
        dates=[r["data"] for r in rows]
        if dates!=sorted(set(dates)):raise ValueError("UNSORTED_OR_DUPLICATE_LEDGER:"+key)
        previous=None;count=0
        for row in rows:
            value=row["navMarkToMarket"]
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError("INVALID_NAV:"+key)
            if previous is not None:
                expected=(value/previous["navMarkToMarket"]-1)*100
                delta=row["retornoDia"]-expected
                if abs(delta)>0.001:
                    report["daily_return_correction_candidates"].append({
                        "ledger":key,"date":row["data"],"previous_date":previous["data"],
                        "published_return_pct":row["retornoDia"],"nav_ratio_return_pct":expected,
                        "difference_pp":delta,"previous_nav":previous["navMarkToMarket"],
                        "current_nav":value,"status":"ARITHMETIC_RECONCILIATION_ONLY_REQUIRES_SOURCE_PATCH"})
                    count+=1
            previous=row
        if not rows:continue
        last=rows[-1];cost=last.get("custosModelo")
        report["ledgers"].append({"ledger":key,"rows":len(rows),"first_date":rows[0]["data"],
            "last_date":last["data"],"nav_mark_to_market":last["navMarkToMarket"],
            "ledger_window_gross_return_pct":100*(last["navMarkToMarket"]/rows[0]["navMarkToMarket"]-1),
            "daily_return_mismatches":count,
            "net_status":"ESTIMATED_MODEL_NOT_OBSERVED" if cost else "N_D_NO_BOUND_COST_MODEL",
            "model_net_mtm":last.get("navMarkToMarketLiquidoEstimado"),"cost_model":cost})
    combined=ledgers.get("ledger_diario_G_COMBINED_v1",[])
    g100={r["data"]:r for r in ledgers.get("ledger_diario_G_100_v1",[])}
    g300={r["data"]:r for r in ledgers.get("ledger_diario_G_300_v1",[])}
    parity=[]
    for row in combined:
        day=row["data"]
        if day not in g100 or day not in g300:continue
        for field in ["navMarkToMarket","navMarkToMarketLiquidoEstimado"]:
            if all(field in r for r in [row,g100[day],g300[day]]):
                delta=row[field]-(g100[day][field]+g300[day][field])/2
                if abs(delta)>1e-6:parity.append({"date":day,"field":field,"delta":delta})
    report["combined_50_50_parity_mismatches"]=parity
    report["ledger_count"]=len(report["ledgers"])
    report["net_model_coverage"]=sum(r["net_status"]=="ESTIMATED_MODEL_NOT_OBSERVED" for r in report["ledgers"])
    report["summary_btc_fields_present"]=sum(s.get("btcRetornoMesmoPeriodoPct") is not None and s.get("alphaVsBtcPct") is not None for s in backup["resumoLedger"])
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--backup",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if a.output.resolve()==a.backup.resolve():raise ValueError("OUTPUT_CANNOT_REPLACE_BACKUP")
    report=audit(a.backup);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes((json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({k:v for k,v in report.items() if k!="ledgers"},ensure_ascii=True))
if __name__=="__main__":main()
