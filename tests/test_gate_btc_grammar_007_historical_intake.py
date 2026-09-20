import json
from pathlib import Path
import tools.gate_btc_factory.grammar_007_historical_intake as m

def test_007_intake_contract(tmp_path, monkeypatch):
 q=tmp_path/"q.json"; out=tmp_path/"out.json"
 fam=[]
 for fid,ch,sources in [
  ("XAGRAMMAR_728DC88D691B","BCB_FOCUS_EXPECTATIONS_REVISION_B3_TRANSMISSION",["BCB","B3"]),
  ("XAGRAMMAR_62943307741A","CVM_FUND_FLOW_B3_TRANSMISSION",["CVM","B3"])]:
  fam.append({"family_id":fid,"channel_id":ch,"grammar_signature":"sig-"+fid,
   "frozen_semantics":{"feature":"f","window":"w","lookback":"l","target":"t"},
   "qualified_sources":sources,"semantic_prereg_sha256":"abc","status":"SOURCE_COST_QUALIFIED",
   "source_qualified":True,"cost_applicability_proven":True,"economics_read":False,
   "historical_testing_started":False})
 q.write_text(json.dumps({"families":fam}))
 monkeypatch.setattr("sys.argv",["x","--qualification",str(q),"--out",str(out)])
 assert m.main()==0
 z=json.loads(out.read_text())
 assert z["status"]=="READY_FOR_CAUSAL_SOURCE_MATERIALIZATION"
 assert z["economics_read"] is False and z["outcomes_read"] is False
 assert z["historical_testing_started"] is False
 assert {x["family_id"] for x in z["families"]}==m.ALLOWED
 assert all(x["next_stage"]=="CAUSAL_SOURCE_MATERIALIZATION_BEFORE_DISCOVERY" for x in z["families"])
 assert z["safety"]["NO_RETUNE"] is True and z["safety"]["NO_BACKFILL"] is True
