#!/usr/bin/env python3
"""Prospective-only BCB Focus feature collector for XAGRAMMAR_728DC88D691B."""
import argparse,json,urllib.parse,urllib.request,hashlib
from datetime import date,datetime,timezone
from pathlib import Path
BASE="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
FID="XAGRAMMAR_728DC88D691B"
def query(ind):
 f=urllib.parse.quote(f"Indicador eq '{ind}' and baseCalculo eq 0",safe="")
 u=f"{BASE}?$format=json&$top=200&$orderby=Data desc&$filter={f}"
 with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"QRDS-GATE-BTC-RESEARCH-ONLY/1.0"}),timeout=60) as r:return json.loads(r.read())["value"],u
def series(rows,ref):
 d={}
 for x in rows:
  if str(x.get("DataReferencia"))!=ref:continue
  day=str(x.get("Data",""))[:10]
  try:v=float(str(x["Mediana"]).replace(",","."))
  except:continue
  d.setdefault(day,set()).add(v)
 return [(k,next(iter(v))) for k,v in sorted(d.items()) if len(v)==1]
def build(prereg):
 act=datetime.fromisoformat(prereg["activation_utc"].replace("Z","+00:00")).date(); ref=str(act.year)
 ip,iu=query("IPCA"); se,su=query("Selic"); a=series(ip,ref);b=series(se,ref); ai=dict(a);bi=dict(b)
 common=sorted(set(ai)&set(bi)); eligible=[d for d in common if date.fromisoformat(d)>=act]
 obs=[]
 for d in eligible:
  prev=[x for x in common if x<d]
  if not prev:continue
  p=prev[-1];obs.append({"publication_data_date":d,"previous_publication_data_date":p,
   "IPCA_CURRENT_YEAR_MEDIAN_REVISION":ai[d]-ai[p],"SELIC_CURRENT_YEAR_END_MEDIAN_REVISION":bi[d]-bi[p],
   "baseCalculo":0,"family_id":FID,"scientific_credit":0})
 out={"schema":"qrds.factory.grammar_007.focus_prospective_capture.v1","family_id":FID,"activation_utc":prereg["activation_utc"],
 "captured_at_utc":datetime.now(timezone.utc).isoformat(),"status":"PROSPECTIVE_OBSERVATIONS_CAPTURED" if obs else "NO_NEW_ELIGIBLE_PUBLICATION",
 "observations":obs,"observation_count":len(obs),"source_urls":{"IPCA":iu,"Selic":su},"collection_started":True,
 "scientific_credit":0,"prospective_credit":0,"outcomes_read":False,"economics_read":False,"promotion_authority":False,"safety":prereg["safety"]}
 out["capture_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest();return out
def main():
 p=argparse.ArgumentParser();p.add_argument("--prereg",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
 o=build(json.loads(a.prereg.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(o,indent=2,sort_keys=True)+"\n");print(json.dumps({"status":o["status"],"observations":o["observation_count"],"credit":0}))
if __name__=="__main__":main()
