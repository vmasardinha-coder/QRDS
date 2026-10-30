"""Read-only M5 exit research. No terminal connection, orders or source writes."""
import csv, hashlib, json, math, statistics, html
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

STEP=timedelta(minutes=5)
SCENARIOS={'REF':(2,0),'STRESS':(3,0),'DELAYED':(2,1)}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
def plus(ts,n):return (datetime.fromisoformat(ts)+timedelta(minutes=n)).isoformat()
def grid(start,end):
    t=datetime.fromisoformat(start);end=datetime.fromisoformat(end)
    while t<=end:yield t.isoformat();t+=STEP
def trigger(pnl,peak,rule):
    if rule.get('stop') is not None and pnl<=-rule['stop']:return 'STOP'
    if rule.get('target') is not None and pnl>=rule['target']:return 'TARGET'
    if rule.get('arm') is not None and peak>=rule['arm'] and pnl<=peak-rule['distance']:return 'TRAIL'
    return None
def amount(t,price):return t['side']*(price-t['ep'])*t['point']-t['cost']

def prepare(row,session,policy,prices,scenario):
    """Entry, direction and identity come from the existing observed contract."""
    o=next((o for o in row['outcomes'] if o['horizon_minutes']==120 and o['state']=='MODEL_CLOSED'),None)
    if o is None:raise ValueError('NO_CLOSED_120_PATH')
    fee,delay=SCENARIOS[scenario];prefix='delayed_' if delay else ''
    entry=o[prefix+'entry_timestamp'];ep=o[prefix+'entry_price'];point=o.get('value_per_point_brl')
    if not point or point<=0:raise ValueError('UNVERIFIED_POINT_VALUE')
    for ts in grid(entry,plus(entry,125)):
        if ts not in prices:raise ValueError('MISSING_M5:'+ts)
    if abs(prices[entry]-ep)>1e-8:raise ValueError('ENTRY_SOURCE_MISMATCH')
    return {'family_id':row['family_id'],'policy':policy,'session':session,'entry':entry,'ep':ep,'side':row['side'],'point':point,'cost':ep*point*fee/10000,'feature':row['feature'],'window':row['window'],'lookback':row['lookback'],'scenario':scenario}

def simulate(trades,prices,rule,cap=None,priority=()):
    """Chronological M5 book. Conditional decisions fill one bar later, even if
    the target disappears. Time exits are fixed in advance. Slots free on fill.
    No high/low extrema are used to invent fills or simultaneous basket peaks.
    """
    if not trades:return {'state':'NO_TRIGGERS','net_brl':0.,'curve':[],'positions':[],'accepted':0,'max_contracts':0,'skipped_cap':0,'skipped_lock':0}
    ranks={fid:i for i,fid in enumerate(priority)}
    ordered=sorted(trades,key=lambda t:(t['entry'],ranks.get(t['family_id'],len(ranks)),int(t['family_id'][1:])))
    start=ordered[0]['entry'];end=max(plus(t['entry'],rule['minutes']+5) for t in ordered)
    for ts in grid(start,end):
        if ts not in prices:raise ValueError('MISSING_CLOCK_BAR:'+ts)
    arrivals=defaultdict(list)
    for t in ordered:arrivals[t['entry']].append(t)
    active=[];closed=[];curve=[];realized=0.;peaks=defaultdict(float);peak=0.;dd=0.;max_gross=0;max_net=0;max_notional=0.;locked=False;skipped_cap=0;skipped_lock=0;concentration=Counter();events=[]
    def close(t,ts,why):
        nonlocal realized
        net=amount(t,prices[ts]);realized+=net
        closed.append({**{k:v for k,v in t.items() if k not in ['peak','observations']},'exit':ts,'exit_price':prices[ts],'net_brl':net,'gross_brl':net+t['cost'],'reason':why,'sampled_mfe_brl':max(t['observations']+[net]),'sampled_mae_brl':min(t['observations']+[net]),'ever_sampled_positive':max(t['observations']+[net])>0})
        events.append({'timestamp':ts,'event':'EXIT','family_id':t['family_id'],'reason':why,'net_brl':net})
    for ts in grid(start,end):
        remaining=[]
        for t in active:
            if t.get('due') and ts>=t['due']:close(t,ts,t['decision'])
            elif ts>=t['deadline']:close(t,ts,'TIME')
            else:remaining.append(t)
        active=remaining
        for src in arrivals.get(ts,[]):
            if locked:skipped_lock+=1;continue
            if cap is not None and len(active)>=cap:skipped_cap+=1;continue
            t={**src,'deadline':plus(ts,rule['minutes']),'peak':0.,'observations':[],'due':None};active.append(t);events.append({'timestamp':ts,'event':'ENTRY','family_id':t['family_id']})
        floating=sum(amount(t,prices[ts]) for t in active);equity=realized+floating;peak=max(peak,equity);dd=min(dd,equity-peak)
        gross=len(active);net=sum(t['side'] for t in active);max_gross=max(max_gross,gross);max_net=max(max_net,abs(net));max_notional=max(max_notional,sum(abs(prices[ts]*t['point']) for t in active))
        curve.append({'timestamp':ts,'equity_brl':equity,'realized_brl':realized,'floating_brl':floating,'gross_contracts':gross,'net_contracts':net})
        for t in active:
            val=amount(t,prices[ts]);t['observations'].append(val);t['peak']=max(t['peak'],val);concentration[t['family_id']]+=1
        scope=rule.get('scope','family')
        if scope=='family':
            for t in active:
                if t['due']:continue
                why=trigger(amount(t,prices[ts]),t['peak'],rule)
                if why:t['due']=plus(ts,5);t['decision']=why;events.append({'timestamp':ts,'event':'DECISION','family_id':t['family_id'],'reason':why,'observed_brl':amount(t,prices[ts])})
        else:
            keys=set(t['entry'] for t in active) if scope=='cohort' else {'DAY'}
            for key in keys:
                members=[t for t in active if scope=='day' or t['entry']==key]
                if not members or any(t['due'] for t in members):continue
                val=equity if scope=='day' else sum(amount(t,prices[ts]) for t in members)+sum(c['net_brl'] for c in closed if c['entry']==key)
                peaks[key]=max(peaks[key],val);why=trigger(val,peaks[key],rule)
                if why:
                    for t in members:t['due']=plus(ts,5);t['decision']=why+'_LOT'
                    events.append({'timestamp':ts,'event':'LOT_DECISION','lot':key,'reason':why,'observed_brl':val})
                    if scope=='day':locked=True
    if active:raise ValueError('UNCLOSED_POSITION')
    total=sum(concentration.values());hhi=sum((x/total)**2 for x in concentration.values()) if total else None
    return {'state':'MODEL_REPLAY_COMPLETE','net_brl':realized,'gross_brl':sum(t['gross_brl'] for t in closed),'cost_brl':sum(t['cost'] for t in closed),'drawdown_brl':dd,'max_contracts':max_gross,'max_abs_net_contracts':max_net,'max_notional_brl':max_notional,'accepted':len(closed),'skipped_cap':skipped_cap,'skipped_lock':skipped_lock,'concentration_hhi':hhi,'correlation':None,'margin_required_brl':None,'goal_hit_sampled':any(p['equity_brl']>=150 for p in curve),'day_locked':locked,'curve':curve,'positions':closed,'events':events}

def csvout(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for row in rows for k,v in row.items() if not isinstance(v,(list,dict))))
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',delimiter=';');w.writeheader();w.writerows(rows)

def build(root,cfg=None,records=None,bar_files=None):
    root=Path(root);out=root/'reports';out.mkdir(exist_ok=True);spec_path=Path(__file__).with_name('EXIT_RESEARCH_V1.json');spec=read(spec_path);sha=hashlib.sha256(spec_path.read_bytes()).hexdigest()
    if records is None:records=[read(p) for p in sorted((root/'ledger').glob('*/*.json'))]
    if bar_files is None:
        bar_files={}
        for p in sorted((root/'captures').glob('*.json')):
            r=read(p)
            if len(r['rows'])>len(bar_files.get(r['session'],{}).get('rows',[])):bar_files[r['session']]=r
    paths=[];family_results=[];lot_runs=[];invalid=[];counts=[]
    for rec in records:
        if rec.get('kind')!='POST_ACTIVATION_OBSERVATION':raise ValueError('NOT_A_POST_ACTIVATION_SOURCE')
        day=rec['session'];pol=rec['policy'];raw=bar_files.get(day);prices={r['timestamp']:float(r['open']) for r in raw['rows']} if raw else {}
        selected=[r for r in rec['families'] if r['state']=='TRIGGER'];tag='DEVELOPMENT_REPLAY' if day<spec['post_freeze_not_before'] else 'POST_FREEZE_EXIT_REPLAY'
        counts.append({'session':day,'policy':pol,**dict(Counter(r['state'] for r in rec['families']))})
        for scenario in SCENARIOS:
            trades=[]
            for row in selected:
                try:t=prepare(row,day,pol,prices,scenario)
                except ValueError as e:invalid.append({'session':day,'policy':pol,'family_id':row['family_id'],'scenario':scenario,'reason':str(e)});continue
                trades.append(t)
                curve=[[ts,amount(t,prices[ts])] for ts in grid(t['entry'],plus(t['entry'],120))]
                paths.append({**t,'evaluation':tag,'curve':curve,'max_sampled_brl':max(x[1] for x in curve),'min_sampled_brl':min(x[1] for x in curve),'positive_sampled':any(x[1]>0 for x in curve)})
                for rule in spec['family_rules']:
                    r=simulate([t],prices,rule);c=r['positions'][0]
                    family_results.append({'session':day,'policy':pol,'evaluation':tag,'family_id':t['family_id'],'scenario':scenario,'rule':rule['id'],'minutes':rule['minutes'],'entry':c['entry'],'exit':c['exit'],'decision':c.get('decision'),'decision_due':c.get('due'),'reason':c['reason'],'net_brl':c['net_brl'],'gross_brl':c['gross_brl'],'cost_brl':c['cost'],'sampled_mfe_brl':c['sampled_mfe_brl'],'sampled_mae_brl':c['sampled_mae_brl'],'ever_sampled_positive':c['ever_sampled_positive']})
            if len(trades)!=len(selected):
                invalid.append({'session':day,'policy':pol,'scenario':scenario,'reason':'LOT_OMITTED_DUE_TO_INCOMPLETE_MEMBER_DATA'});continue
            for cap in spec['caps']:
                for rule in spec['portfolio_rules']:
                    r=simulate(trades,prices,rule,cap,spec['priority_families']);lot_runs.append({'session':day,'policy':pol,'evaluation':tag,'scenario':scenario,'rule':rule['id'],'scope':rule['scope'],'cap':cap,**r})
    stats=[]
    for key in sorted(set((x['session'],x['policy']) for x in family_results)):
        for h in [30,60,120]:
            rows=[x for x in family_results if (x['session'],x['policy'])==key and x['scenario']=='REF' and x['rule']=='TIME'+str(h)]
            stats.append({'session':key[0],'policy':key[1],'minutes':h,'closed':len(rows),'positive_at_exit':sum(r['net_brl']>0 for r in rows),'positive_at_any_sample':sum(r['ever_sampled_positive'] for r in rows),'negative_at_exit_after_sampled_profit':sum(r['net_brl']<0 and r['ever_sampled_positive'] for r in rows)})
    result={'schema':'pressure_valve.intracycle.research.v1','spec':spec,'spec_sha256':sha,'orders':0,'canonical_credit':0,'execution':'M5_MARK_AND_NEXT_BAR_CONDITIONAL_FILL','live_selector_implemented':False,'latest_session':max((r['session'] for r in records),default=None),'counts':counts,'stats':stats,'family_paths':paths,'family_results':family_results,'lot_runs':lot_runs,'invalid':invalid,'qa_limit':'Strict session QA is retrospective; no live selection claims.','point_value_brl':.2}
    write(out/'INTRACYCLE_RESEARCH.json',result);csvout(out/'INTRACYCLE_FAMILY_RESULTS.csv',family_results);csvout(out/'INTRACYCLE_LOTS.csv',lot_runs);csvout(out/'INTRACYCLE_STATS.csv',stats)
    render(out/'INTRACYCLE.html',result)
    write(out/'INTRACYCLE_STATUS.json',{'state':'RESEARCH_UPDATED','latest_session':result['latest_session'],'paths':len(paths),'family_comparisons':len(family_results),'lot_comparisons':len(lot_runs),'invalid':len(invalid),'spec_sha256':sha,'orders':0})
    return result

def render(path,data):
    assets=Path(__file__).with_name('intracycle_template.html').read_text(encoding='utf-8')
    Path(path).write_text(assets.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')),encoding='utf-8')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();r=build(a.root);print(json.dumps({'session':r['latest_session'],'family_results':len(r['family_results']),'lot_runs':len(r['lot_runs']),'invalid':len(r['invalid']),'orders':0}))
