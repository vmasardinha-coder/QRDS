import importlib.util,json,zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; TOOL=ROOT/'tools/gate_btc_qos_prospective_three_track.py'; CONTRACT=ROOT/'migration/GATE_BTC_QOS_PROSPECTIVE_THREE_TRACK_CONTRACT_V1.json'
spec=importlib.util.spec_from_file_location('three_track',TOOL); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def state():
    s={'schema':'gate-btc.qos-prospective-three-track.signal-state.v1','signal_date':'2026-08-31','boundary_date':'2026-09-30','upstream_immutable_snapshot_id':'TEST','v2a_zip_sha256':'x','required_file_sha256':{},'v2a_version':'TEST','raw_attempted_symbols':100,'raw_loaded_symbols':100,'raw_coverage_ratio':1.0,'raw_coverage_reference_min':.95,'raw_coverage_quality':'HIGH_GE95','admissible':True,'admission_reason':'PASS_STRUCTURAL_POINT_IN_TIME_CAPTURE','candidate_count':3,'candidate_symbols':['AAA','BBB','CCC'],'candidate_source_lock':{'AAA':'S','BBB':'S','CCC':'S'},'qos_picks':{'QOS_Moderada':['AAA','BBB'],'QOS_Ultra':['AAA','CCC']},'scope':'ALT_SLEEVE_SELECTOR_AND_EXIT_LAYER_ONLY','research_only':True,'shadow_only':True,'not_approved':True,'orders_generated':0,'real_capital_used':0}; s['state_sha256']=mod.sha_row(s); return s

def prices():
    rows=[]; paths={'AAA':[('2026-09-01',100),('2026-09-10',130),('2026-09-15',110),('2026-09-16',108),('2026-10-01',120)],'BBB':[('2026-09-01',100),('2026-09-15',105),('2026-10-01',110)],'CCC':[('2026-09-01',100),('2026-09-20',95),('2026-10-01',90)]}
    for a,xs in paths.items():
        for d,p in xs: rows.append({'date':d,'symbol':a,'close_usd':p,'source':'S'})
    return pd.DataFrame(rows)

def daily_master():
    rows=[]
    for d in pd.date_range('2026-08-31','2026-10-01'):
        for a in ('AAA','BBB','CCC'):
            if a=='AAA': p=100 if d<pd.Timestamp('2026-09-10') else 130 if d<=pd.Timestamp('2026-09-14') else 110 if d==pd.Timestamp('2026-09-15') else 108 if d==pd.Timestamp('2026-09-16') else 120 if d==pd.Timestamp('2026-10-01') else 100
            elif a=='BBB': p=100 if d<pd.Timestamp('2026-10-01') else 110
            else: p=100 if d<pd.Timestamp('2026-10-01') else 90
            rows.append({'date':d,'symbol':a,'close_usd':p,'source':'S'})
    return pd.DataFrame(rows)

def write_v2a(path,day,master):
    def csv(x): return x.to_csv(index=False).encode()
    q=pd.DataFrame([{'attempted_symbols':150,'loaded_symbols':94,'failed_symbols':56,'coverage_ratio':94/150}]); raw=pd.DataFrame([{'symbol':a} for a in ('AAA','BBB','CCC')]); f=pd.DataFrame([{'symbol':a,'is_core':False,'is_stable':False,'is_blocked':False} for a in ('AAA','BBB','CCC')]); p=pd.DataFrame([{'strategy':'QOS_Moderada','asset':'AAA','weight':.5},{'strategy':'QOS_Moderada','asset':'BBB','weight':.5},{'strategy':'QOS_Ultra','asset':'AAA','weight':.5},{'strategy':'QOS_Ultra','asset':'CCC','weight':.5}]); h=master[pd.to_datetime(master.date)<=pd.Timestamp(day)]
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('outputs/v2a_run_manifest.json',json.dumps({'version':'TEST','data_as_of':pd.Timestamp(day).date().isoformat()})); z.writestr('outputs/data_quality_summary.csv',csv(q)); z.writestr('data/raw/coingecko_current_universe_v04.csv',csv(raw)); z.writestr('data/processed/qos_v2a_current_features.csv',csv(f)); z.writestr('outputs/qos_v2a_current_portfolios.csv',csv(p)); z.writestr('data/processed/qos_v2a_master_daily.csv',csv(h))

def test_contract():
    c=mod.read_contract(CONTRACT); assert c['safety']['orders_generated']==0 and c['point_in_time_universe']['raw_coverage_role']=='DATA_QUALITY_DIAGNOSTIC_NOT_SIGNAL_ADMISSION_GATE'

def test_three_track_math_and_prl50(tmp_path):
    rows,detail=mod.evaluate_cycle(state(),mod.read_contract(CONTRACT),prices()); r=next(x for x in rows if x['strategy']=='QOS_Moderada'); assert abs(r['pit_control_return']-(.2+.1-.1)/3)<1e-12 and abs(r['qos_control_return']-.15)<1e-12 and abs(r['qos_prl50_return']-.09)<1e-12; assert detail['strategy_outcomes']['QOS_Moderada']['AAA']['prl_exit_date']=='2026-09-16'; led=tmp_path/'l.json'; mod.append_ledger(led,rows,state()['state_sha256'])
    try: mod.append_ledger(led,rows,state()['state_sha256']); assert False
    except RuntimeError as e: assert 'duplicate cycle append forbidden' in str(e)

def test_source_substitution_fails():
    x=prices(); x.loc[(x.symbol=='AAA')&(x.date=='2026-09-16'),'source']='OTHER'
    try: mod.evaluate_cycle(state(),mod.read_contract(CONTRACT),x); assert False
    except RuntimeError as e: assert 'source substitution' in str(e)

def test_unresolved_control_never_dropped():
    s=state(); s['candidate_count']=4; s['candidate_symbols'].append('DDD'); s['candidate_source_lock']['DDD']='S'; s['state_sha256']=mod.sha_row(s); rows,detail=mod.evaluate_cycle(s,mod.read_contract(CONTRACT),prices()); r=rows[0]; assert r['selector_alpha'] is None and r['prl50_alpha'] is not None and detail['unresolved_candidates']==['DDD']

def test_missing_selected_fails():
    x=prices(); x=x[x.symbol!='AAA']
    try: mod.evaluate_cycle(state(),mod.read_contract(CONTRACT),x); assert False
    except RuntimeError as e: assert 'selected price history missing' in str(e)

def test_archive_append_and_evaluate(tmp_path):
    s=state(); c=mod.read_contract(CONTRACT); ar=tmp_path/'a'; mod.initialize_cycle_archive(s,ar); m=daily_master()
    for d in pd.date_range('2026-08-31','2026-10-01'): assert mod.append_path_snapshot(s,ar,m,d,f'R-{d.date()}')['result']=='APPENDED'
    assert mod.append_path_snapshot(s,ar,m,pd.Timestamp('2026-10-01'),'R-2026-10-01')['result']=='DUPLICATE_IDENTICAL'; st,rows,_=mod.evaluate_cycle_from_archive(s,c,ar); assert st=='PASS_COMPLETED_CYCLE' and len(rows)==2

def test_archive_gap_fails(tmp_path):
    s=state(); ar=tmp_path/'a'; mod.initialize_cycle_archive(s,ar); m=daily_master(); mod.append_path_snapshot(s,ar,m,pd.Timestamp('2026-08-31'),'R0')
    try: mod.append_path_snapshot(s,ar,m,pd.Timestamp('2026-09-02'),'R2'); assert False
    except RuntimeError as e: assert 'daily gap/backfill prohibited' in str(e)

def test_selected_daily_gap_blocks(tmp_path):
    s=state(); ar=tmp_path/'a'; mod.initialize_cycle_archive(s,ar); m=daily_master(); m=m[~((m.symbol=='AAA')&(m.date==pd.Timestamp('2026-09-12')))]
    for d in pd.date_range('2026-08-31','2026-10-01'): mod.append_path_snapshot(s,ar,m,d,f'R-{d.date()}')
    st,rows,detail=mod.evaluate_cycle_from_archive(s,mod.read_contract(CONTRACT),ar); assert st=='BLOCKED_SELECTED_DAILY_PATH_GAP' and not rows and detail['symbol']=='AAA'

def test_process_daily_automation(tmp_path):
    c=mod.read_contract(CONTRACT); m=daily_master(); rt=tmp_path/'rt'
    for d in pd.date_range('2026-08-31','2026-10-01'):
        z=tmp_path/f'{d.date()}.zip'; write_v2a(z,d,m); assert mod.process_daily(z,c,rt,d,f'R-{d.date()}')['status']=='PASS_DAILY_PROCESS'
    led=json.loads((rt/'RESULT_LEDGER.json').read_text()); st=json.loads((rt/'STATUS.json').read_text()); by={x['signal_date']:x['status'] for x in st['cycles']}; assert len(led)==2 and by['2026-08-31']=='COMPLETED' and by['2026-09-30']=='WAITING_CYCLE_COMPLETION'
