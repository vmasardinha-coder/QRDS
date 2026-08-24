#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

EXPECTED_HASH='b9e60d46a39a60c2e1d440b18a4a6a98883849f1de2b4c3d0ab06a48e849bfbd'

def canon_rule(f):
 keys=['schema','source_issue','source_generation','source_pr','signal_asset','observation_minutes','trigger_abs_standardized_impulse_gte','standardizer','traded_asset','direction','execution','hold_minutes','reference_roundtrip_cost_bp','stress_roundtrip_cost_bp','orders','real_capital','engine_feed','not_approved']
 d={k:f[k] for k in keys}
 return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main(freeze_path,status_out):
 f=json.load(open(freeze_path))
 assert canon_rule(f)==EXPECTED_HASH==f['rule_hash_sha256']
 assert f['clock_status']=='NOT_STARTED_SOURCE_UNBOUND'
 assert f['eligible_observations']==0
 assert f['append_only'] and f['backfill_forbidden'] and f['retune_forbidden'] and f['partial_prospective_feedback_forbidden']
 assert f['h1_economics_read'] is False
 assert f['orders']==0 and f['real_capital']==0 and f['engine_feed'] is False and f['not_approved'] is True
 s={'schema':'gate_btc.b3.h31.prospective_status.v1','status':'BLOCKED_SOURCE_ADAPTER_NOT_BOUND','clock_started':False,'eligible_observations':0,'freeze_hash_sha256':EXPECTED_HASH,'h1_economics_read':False,'partial_prospective_economics_exposed':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
 Path(status_out).write_text(json.dumps(s,indent=2,sort_keys=True)+'\n');print(json.dumps(s,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--freeze',default='research/b3_h31_prospective_freeze.json');p.add_argument('--status-out',required=True);a=p.parse_args();main(a.freeze,a.status_out)
