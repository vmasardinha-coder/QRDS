"""First outcome read of a hash-bound cross-venue checkpoint; no live orders."""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

CHANNEL='CRYPTO_CROSS_VENUE_PRICE_DISCOVERY'
SAFETY={'research_only':True,'shadow_only':True,'orders':0,'real_capital':0,'engine_feed':False,'promotion_authority':False}

def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+'\n')
def ms(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)

def qualify_observation(o):
    """Source/clock checks only, before any return arithmetic."""
    why=[]
    try:
        boundary=int(o['observation_id']);decision=int(o['decision_ms'])
        if decision!=boundary+5000:why.append('DECISION_CLOCK_MISMATCH')
        for name,at in [('source_previous_close',boundary-60000),('execution_previous_close',boundary-60000),('source_close',boundary),('execution_close',boundary)]:
            e=o[name];stamp=int(e['ts_ms'])
            if not at-5000<=stamp<=at:why.append(name+':PRICE_AGE')
            if int(e['first_seen_receipt_ms'])>decision:why.append(name+':NOT_AVAILABLE_AT_DECISION')
            if int(e['first_seen_receipt_ms'])<stamp:why.append(name+':FUTURE_EVENT_AT_RECEIPT')
        entry=o['entry'];exit_=o['exit'];begin=int(entry['ts_ms']);end=int(exit_['ts_ms'])
        if not decision<=begin<=decision+5000:why.append('ENTRY_CLOCK')
        if not begin+60000<=end<=begin+65000:why.append('EXIT_CLOCK')
        for name in ('source_previous_close','execution_previous_close','source_close','execution_close','entry','exit'):
            value=float(o[name]['price'])
            if not math.isfinite(value) or value<=0:why.append('INVALID_PRICE:'+name)
    except (KeyError,TypeError,ValueError):why.append('REQUIRED_SOURCE_CLOCK_EVIDENCE_MISSING')
    return sorted(set(why))

def load_bound(root,prereg):
    b=read(root/'DATASET_BINDING_N1440.json')
    if sha(canonical({k:v for k,v in b.items() if k!='binding_payload_sha256'}))!=b.get('binding_payload_sha256'):raise ValueError('BINDING_HASH')
    c=read(prereg)
    if sha(prereg.read_bytes())!=b['prereg_sha256']:raise ValueError('PREREG_HASH')
    if b['channel_id']!=CHANNEL or c['channel_id']!=CHANNEL:raise ValueError('CHANNEL_ID')
    if sha((root.parent.parent/'SOURCE_COST.json').read_bytes())!=b['source_cost_file_sha256']:raise ValueError('ADMISSION_HASH')
    admission=read(root.parent.parent/'SOURCE_COST.json')
    if not any(x.get('channel_id')==CHANNEL and x.get('adjudication_decision')=='SOURCE_COST_QUALIFIED' for x in admission['channels']):raise ValueError('ADMISSION_NOT_QUALIFIED')
    objects=[]
    for item in b['partitions']:
        if Path(item['file']).name!=item['file']:raise ValueError('PARTITION_PATH')
        raw=(root/'partitions'/item['file']).read_bytes()
        if sha(raw)!=item['sha256']:raise ValueError('PARTITION_HASH')
        d=json.loads(raw)
        if d.get('channel_id')!=CHANNEL or d.get('economics_read') is not False or d.get('source_cost_evidence_sha256')!=b['source_cost_evidence_sha256']:raise ValueError('PARTITION_AUTHORITY')
        if d.get('schema','').endswith('.v2') and d.get('history_endpoint_used') is not False:raise ValueError('HISTORY_REPAIR')
        objects.append(d)
    # All bound bytes are verified before extracting the frozen unique records.
    seen={}
    for d in objects:
        for o in d.get('observations',[]):
            if o.get('eligible_for_future_evaluation') is True:seen.setdefault(str(o['observation_id']),o)
    ordered=[seen[k] for k in sorted(seen,key=int)]
    if len(ordered)!=b['record_count'] or not ordered:raise ValueError('RECORD_COUNT')
    if int(ordered[0]['observation_id'])!=ms(b['first_eligible_timestamp_utc']) or int(ordered[-1]['observation_id'])!=ms(b['last_eligible_timestamp_utc']):raise ValueError('BOUND_TIME_RANGE')
    minimum=c['evaluation']['minimum_observation_count_before_first_economics']
    if b['checkpoint']!=minimum or minimum!=1440:raise ValueError('CHECKPOINT_MISMATCH')
    valid=[];excluded=[]
    for o in ordered:
        reasons=qualify_observation(o)
        if reasons:excluded.append({'observation_id':o['observation_id'],'reasons':reasons})
        else:valid.append(o)
    return b,c,valid,excluded

def fetch_funding(root,start_ms,end_ms):
    """Retrieve official settled funding, bounded pages, preserving every response."""
    directory=root/'economics/N1440/funding';directory.mkdir(parents=True,exist_ok=True)
    proof=directory/'RECEIPT.json'
    if proof.exists():
        receipt=read(proof)
        if receipt['coverage_start_ms']>start_ms or receipt['coverage_through_ms']<end_ms:raise ValueError('FUNDING_COVERAGE')
        events=[]
        for p in receipt['raw_pages']:
            raw=gzip.decompress((directory/p['file']).read_bytes())
            if sha(raw)!=p['sha256']:raise ValueError('FUNDING_HASH')
            events.extend(json.loads(raw)['data'])
        return normalize_funding(events),receipt
    events=[];proofs=[];cursor=None;oldest=None
    for page in range(5):
        url='https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=100'
        if cursor is not None:url+='&after='+str(cursor)
        with urlopen(Request(url,headers={'User-Agent':'QRDS-Research/1.0'}),timeout=30) as response:raw=response.read()
        d=json.loads(raw)
        if d.get('code')!='0' or not d.get('data'):raise ValueError('FUNDING_UNAVAILABLE')
        items=d['data']
        if any(x.get('instId')!='BTC-USDT-SWAP' for x in items):raise ValueError('FUNDING_INSTRUMENT')
        new_oldest=min(int(x['fundingTime']) for x in items)
        if oldest is not None and new_oldest>=oldest:raise ValueError('FUNDING_CURSOR')
        oldest=new_oldest;events.extend(items)
        name=f'page_{page:02}.json.gz';(directory/name).write_bytes(gzip.compress(raw,mtime=0))
        proofs.append({'file':name,'sha256':sha(raw),'url':url})
        if oldest<=start_ms:break
        cursor=oldest;time.sleep(.2)
    if oldest is None or oldest>start_ms:raise ValueError('FUNDING_HISTORY_INCOMPLETE')
    receipt={'schema':'qrds.crypto745.official_funding_receipt.v1','instrument':'BTC-USDT-SWAP',
             'coverage_start_ms':oldest,'coverage_through_ms':int(datetime.now(timezone.utc).timestamp()*1000),'raw_pages':proofs}
    if receipt['coverage_through_ms']<end_ms:raise ValueError('FUNDING_NOT_MATURE')
    save(proof,receipt)
    return normalize_funding(events),receipt

def normalize_funding(events):
    seen={}
    for e in events:
        rate=float(e['fundingRate']);stamp=int(e['fundingTime'])
        if not math.isfinite(rate):raise ValueError('FUNDING_NONFINITE')
        if stamp in seen and seen[stamp]!=rate:raise ValueError('FUNDING_CONFLICT')
        seen[stamp]=rate
    return sorted(seen.items())

def evaluate_one(o,funding,c):
    scalar=math.log(float(o['source_close']['price'])/float(o['source_previous_close']['price']))-math.log(float(o['execution_close']['price'])/float(o['execution_previous_close']['price']))
    side=1 if scalar>0 else -1 if scalar<0 else 0
    ratio=float(o['exit']['price'])/float(o['entry']['price'])
    gross=side*(ratio-1)
    # Frozen cost quote is round-trip bps per unit entry notional, not observed fees.
    cost=(c['cost_model']['execution_round_trip_bps']+c['cost_model']['additional_slippage_round_trip_bps'])/10000 if side else 0
    carry=sum(rate for stamp,rate in funding if int(o['entry']['ts_ms'])<stamp<=int(o['exit']['ts_ms']))
    funding_return=-side*carry
    return {'observation_id':o['observation_id'],'side':side,'gross':gross,'cost':cost,
            'funding_model_return':funding_return,'net_model':gross-cost+funding_return}

def run(root,prereg):
    b,c,valid,excluded=load_bound(root,prereg)
    folder=root/'economics/N1440';folder.mkdir(parents=True,exist_ok=True)
    quality={'schema':'qrds.crypto745.bound_source_clock_review.v1','binding_payload_sha256':b['binding_payload_sha256'],
             'claimed_eligible':b['record_count'],'clock_qualified':len(valid),'excluded_before_outcome_read':excluded,
             'exclusions_use_outcomes':False,'minimum':1440,'safety':SAFETY}
    save(folder/'SOURCE_CLOCK_REVIEW.json',quality)
    if len(valid)<1440:
        report={**quality,'status':'BLOCKED_VALID_SOURCE_COUNT_BELOW_1440','economics_read':False,'economics_computed':False}
        save(folder/'RESULT.json',report);return report
    output=folder/'RESULT.json'
    if output.exists():
        old=read(output)
        if old.get('economics_computed') is True:
            if old.get('binding_payload_sha256')!=b['binding_payload_sha256']:raise ValueError('RESULT_BINDING')
            return old
    funding,proof=fetch_funding(root,min(int(o['entry']['ts_ms']) for o in valid),max(int(o['exit']['ts_ms']) for o in valid))
    outcomes=[evaluate_one(o,funding,c) for o in valid]
    report={'schema':'qrds.crypto745.crossvenue_economic_checkpoint.v1','channel_id':CHANNEL,
      'status':'CHECKPOINT_DESCRIPTIVE_NO_PROMOTION_GATE','checkpoint':1440,
      'binding_payload_sha256':b['binding_payload_sha256'],'prereg_sha256':b['prereg_sha256'],
      'evaluator_sha256':sha(Path(__file__).read_bytes()),'clock_qualified_observations':len(valid),
      'excluded_source_clock_observations':len(excluded),'directions':dict(Counter(str(o['side']) for o in outcomes)),
      'mean_gross_bps':sum(o['gross'] for o in outcomes)/len(outcomes)*10000,
      'mean_net_model_bps':sum(o['net_model'] for o in outcomes)/len(outcomes)*10000,
      'net_win_rate':sum(o['net_model']>0 for o in outcomes)/len(outcomes),
      'net_sum_bps_diagnostic_not_nav':sum(o['net_model'] for o in outcomes)*10000,
      'worst_event_net_bps':min(o['net_model'] for o in outcomes)*10000,
      'best_event_net_bps':max(o['net_model'] for o in outcomes)*10000,
      'funding_sum_model_bps':sum(o['funding_model_return'] for o in outcomes)*10000,
      'funding_receipt_sha256':sha(canonical(proof)),
      'cost_model':'FIXED_24BPS_ROUND_TRIP_PER_UNIT_ENTRY_NOTIONAL; FUNDING_OFFICIAL_RATE_PER_UNIT_NOTIONAL',
      'accounting_limit':'EVENTS_ARE_PAIRED_UNIT_NOTIONAL_DIAGNOSTICS_NOT_COMPOUNDED_NAV_OR_OBSERVED_FILLS',
      'economics_read':True,'economics_computed':True,'scientific_credit':0,'safety':SAFETY,'outcomes':outcomes}
    save(output,report);return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    prereg=Path(__file__).parent/'gate_btc_factory/crypto_challenger_prereg/CRYPTO_CROSS_VENUE_PRICE_DISCOVERY_PREREG.v1.json'
    result=run(args.root,prereg);print(json.dumps({k:v for k,v in result.items() if k not in ('outcomes','excluded_before_outcome_read')},sort_keys=True))
