"""Validate a frozen H31 checkpoint before reading its sealed economics."""
import argparse, hashlib, json, math, statistics
from pathlib import Path


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def checkpoint(root,freeze,n=10):
    if n not in freeze['checkpoints']:
        raise ValueError('CHECKPOINT_NOT_PREREGISTERED')
    status=json.loads((root/'STATUS.json').read_text(encoding='utf-8-sig'))
    paths=sorted((root/'events').glob('*.json'))
    if len(paths)<n or int(status['eligible_observations'])<n:
        raise ValueError('CHECKPOINT_NOT_REACHED_NO_PARTIAL_ECONOMICS')
    if len(paths)!=int(status['eligible_observations']):
        raise ValueError('COUNTER_EVENT_COUNT_MISMATCH')
    events=[];previous=None
    for p in paths:
        event=json.loads(p.read_text(encoding='utf-8-sig'));sealed=dict(event);hashed=sealed.pop('event_hash_sha256',None)
        if hashed!=digest(sealed) or event['previous_event_hash']!=previous:
            raise ValueError('EVENT_HASH_CHAIN_MISMATCH:'+p.name)
        if event['date']!=p.stem or event['freeze_rule_hash_sha256']!=freeze['rule_hash_sha256']:
            raise ValueError('FROZEN_RULE_OR_DATE_MISMATCH')
        if event['h1_economics_read'] is not False or event['orders']!=0 or event['real_capital']!=0 or event['engine_feed'] is not False:
            raise ValueError('SCIENTIFIC_AUTHORITY_CHANGED')
        warm=event['warmup'];dates=warm['trailing_session_dates']
        if len(dates)!=20 or len(set(dates))!=20 or max(dates)>=event['date'] or warm['uses_scored_prospective_rows_for_warmup'] is not False:
            raise ValueError('NONCAUSAL_WARMUP')
        previous=hashed;events.append(event)
    if status['last_event_hash']!=previous or status['latest_date']!=events[-1]['date']:
        raise ValueError('STATUS_EVENT_TAIL_MISMATCH')
    selected=events[:n];trades=[];daily=[]
    for e in selected:
        signal=e['signal'];trigger=abs(float(signal['standardized_impulse']))>=float(freeze['trigger_abs_standardized_impulse_gte'])
        if signal['trigger'] is not trigger:
            raise ValueError('FROZEN_TRIGGER_MISMATCH')
        econ=e['sealed_economics']
        if trigger:
            expected_side=-1 if float(signal['wdo_ret30_bps'])>0 else 1
            if signal['side']!=expected_side:
                raise ValueError('FROZEN_DIRECTION_MISMATCH')
            values=[econ[k] for k in ['gross_bps','reference_net_bps','stress_net_bps']]
            if any(v is None or not math.isfinite(float(v)) for v in values):
                raise ValueError('MISSING_OR_INVALID_SEALED_ECONOMICS')
            gross,ref,stress=map(float,values)
            if not math.isclose(ref,gross-float(freeze['reference_roundtrip_cost_bp']),abs_tol=1e-10) or not math.isclose(stress,gross-float(freeze['stress_roundtrip_cost_bp']),abs_tol=1e-10):
                raise ValueError('FROZEN_COST_MISMATCH')
            trades.append(dict(session=e['date'],gross_bps=gross,reference_net_bps=ref,stress_net_bps=stress));daily.append(ref)
        else:
            if signal['side']!=0 or any(econ[k] is not None for k in ['gross_bps','reference_net_bps','stress_net_bps']):
                raise ValueError('NO_SIGNAL_MUST_NOT_HAVE_TRADE')
            daily.append(0.0)
    net=[t['reference_net_bps'] for t in trades]
    cumulative=0.0;peak=0.0;dd=0.0
    for value in daily:
        cumulative+=value;peak=max(peak,cumulative);dd=min(dd,cumulative-peak)
    return dict(schema='gate_btc.h31.fixed_checkpoint.v1',status='CHECKPOINT_VALIDATED_NO_PROMOTION',checkpoint=n,
        first_session=selected[0]['date'],last_session=selected[-1]['date'],rule_hash=freeze['rule_hash_sha256'],
        integrity='PASS',event_hashes=[e['event_hash_sha256'] for e in selected],observations=n,trades=len(trades),no_signal_observations=n-len(trades),
        gross_bps_sum=sum(t['gross_bps'] for t in trades),reference_net_bps_sum=sum(net),stress_net_bps_sum=sum(t['stress_net_bps'] for t in trades),
        reference_cost_bps_sum=len(trades)*float(freeze['reference_roundtrip_cost_bp']),stress_cost_bps_sum=len(trades)*float(freeze['stress_roundtrip_cost_bp']),
        win_rate=sum(v>0 for v in net)/len(net) if net else None,expectancy_bps_per_trade=statistics.mean(net) if net else None,
        observation_volatility_bps=statistics.stdev(daily) if len(daily)>1 else None,additive_max_drawdown_bps=dd,
        capital_base=None,portfolio_return=None,annualized_sharpe=None,benchmark_comparison=None,
        limitations=['BPS_SUM_IS_NOT_PORTFOLIO_RETURN','NO_PREREGISTERED_PASS_FAIL_THRESHOLDS_SUPPLIED','NO_H1_ECONOMICS_READ'],
        decision='INCONCLUSIVE_NO_PROMOTION_RULE',trade_details=trades,research_only=True,shadow_only=True,not_approved=True,
        engine_feed=False,orders=0,real_capital=0,h1_economics_read=False,counter_changed=False,methodology_changed=False)


def write_once(path,value):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('IMMUTABLE_CHECKPOINT_CHANGED')
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--checkpoint',type=int,default=10);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    value=checkpoint(a.root,json.loads(a.freeze.read_text()),a.checkpoint);write_once(a.out,value)
    print(json.dumps({k:value[k] for k in ['status','checkpoint','observations','trades','reference_net_bps_sum','decision']}))
