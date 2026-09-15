#!/usr/bin/env python3
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
FAMILY='XAWINWDO_REGIME_001'
SAFETY={'h1_h31_untouched':True,'existing_counter_credit':0,'retroactive_credit':0,'no_retune':True,'no_backfill':True,'economics_opened_without_gates':False}
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--runtime',required=True); a=ap.parse_args(); root=Path(a.repo); out=Path(a.runtime); out.parent.mkdir(parents=True,exist_ok=True)
 plan=root/'tools/gate_btc_factory/WIN_WDO_CROSS_ASSET_REGIME_SOURCE_AUDIT_PLAN_20260915.json'
 if not plan.exists(): raise SystemExit('FAIL_CLOSED: canonical source audit plan missing')
 candidates=[]
 for p in root.rglob('*'):
  if not p.is_file() or p==plan: continue
  s=str(p).lower()
  if 'win' in s and 'wdo' in s and any(x in s for x in ('source','qualified','coverage','cost','dataset','manifest')): candidates.append({'path':str(p.relative_to(root)),'sha256':sha(p)})
 source=[x for x in candidates if any(k in x['path'].lower() for k in ('source','qualified','coverage','dataset','manifest'))]
 cost=[x for x in candidates if 'cost' in x['path'].lower()]
 status='SOURCE_COST_AUDIT_BLOCKED'; nxt='QUALIFY_CANONICAL_SOURCE_AND_COSTS'
 if source and cost: status='SOURCE_COST_EVIDENCE_LOCATED_REQUIRES_EXPLICIT_SEMANTIC_AUDIT'; nxt='VERIFY_IDENTITY_TIMEZONE_COVERAGE_COST_SEMANTICS_BEFORE_OUTCOMES'
 d={'schema':'qrds.factory.win_wdo_independent_runtime.v1','family':FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'status':status,'source_evidence':source,'cost_evidence':cost,'source_audit_complete':False,'cost_applicability_proven':False,'historical_testing_started':False,'economics_opened':False,'next_step':nxt,'safety':SAFETY}
 out.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(d,indent=2))
if __name__=='__main__': main()
