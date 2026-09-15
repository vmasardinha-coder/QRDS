#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
FAMILY='XAWINWDO_REGIME_001'
SAFETY={'h1_h31_untouched':True,'existing_counter_credit':0,'retroactive_credit':0,'no_retune':True,'no_backfill':True,'economics_opened_without_gates':False}
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--runtime',required=True); a=ap.parse_args(); root=Path(a.repo); out=Path(a.runtime); out.parent.mkdir(parents=True,exist_ok=True)
 base=root/'tools/gate_btc_factory'
 plan=base/'WIN_WDO_CROSS_ASSET_REGIME_SOURCE_AUDIT_PLAN_20260915.json'
 sourcep=base/'B3_WIN_WDO_OFFICIAL_SOURCE_CONTRACT.v1.json'
 costp=base/'B3_WIN_WDO_COST_PREREG.v1.json'
 for p in (plan,sourcep,costp):
  if not p.exists(): raise SystemExit('FAIL_CLOSED: required frozen evidence missing: '+str(p))
 source=load(sourcep); cost=load(costp)
 ps=source.get('primary_surface',{}); cov=source.get('coverage',{}); tz=source.get('session_and_timezone',{})
 source_ok=(ps.get('owner')=='B3' and ps.get('report')=='BVBG.086.01 PriceReport' and ps.get('coverage_horizon')==['2020-01-01','2024-12-31'] and tz.get('market_timezone')=='America/Sao_Paulo' and cov.get('all_blocks_contract_pass') is True and source.get('source_admission',{}).get('pass') is True)
 cm=cost.get('cost_model',{}); cost_ok=(cm.get('unit')=='BRL_PER_CONTRACT_ROUND_TRIP' and cm.get('WIN')==0.50 and cm.get('WDO')==2.12 and cost.get('scientific_boundary',{}).get('economics_read_before_this_prereg') is False)
 # The old univariate contract forbids cross-asset reads for that old family. We reuse only its already-qualified physical B3 evidence under this independently preregistered family; no old-family outcome/economic state is imported.
 gates=source_ok and cost_ok
 status='SOURCE_COST_AUDIT_PASSED_CROSS_ASSET_FAMILY_READY_FOR_DISCOVERY' if gates else 'SOURCE_COST_AUDIT_BLOCKED'
 d={'schema':'qrds.factory.win_wdo_independent_runtime.v2','family':FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':status,'source_contract':{'path':str(sourcep.relative_to(root)),'sha256':sha(sourcep),'owner':ps.get('owner'),'report':ps.get('report'),'coverage_horizon':ps.get('coverage_horizon'),'timezone':tz.get('market_timezone'),'known_gap_policy':cov.get('known_gap_policy'),'cross_asset_reuse_boundary':'PHYSICAL_SOURCE_EVIDENCE_ONLY_NO_OLD_FAMILY_OUTCOMES'},'cost_contract':{'path':str(costp.relative_to(root)),'sha256':sha(costp),'unit':cm.get('unit'),'WIN':cm.get('WIN'),'WDO':cm.get('WDO'),'result_conditioned':cm.get('result_conditioned')},'source_audit_complete':source_ok,'cost_applicability_proven':cost_ok,'historical_testing_started':False,'economics_opened':False,'next_step':'MATERIALIZE_FROZEN_50_30_20_SPLITS_THEN_DISCOVERY' if gates else 'FAIL_CLOSED_REPAIR_SOURCE_OR_COST_SEMANTICS','safety':SAFETY}
 out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(d,indent=2))
if __name__=='__main__': main()
