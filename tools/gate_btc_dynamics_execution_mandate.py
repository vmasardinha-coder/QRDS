"""One frozen target mandate over the accepted research-only spot simulator.

No strategy default, scheduling, source discovery, approval, persistence/stop
signal generation or production writes. All policy choices must be supplied
in exact preauthorized bytes before the first permitted execution window.
"""
from __future__ import annotations
from dataclasses import replace
import hashlib
import re
from tools import gate_btc_dynamics_spot_accounting as book
from tools import gate_btc_dynamics_target_intake as intake
from tools import gate_btc_dynamics_source_costs as costs
from tools import gate_btc_dynamics_market_checked_rebalance as market

SCHEMA='gate_btc.dynamics_exact_target_execution_mandate.v1'
FIELDS={'schema','mandate_id','profile','protocol_sha256','target_admission_sha256',
        'cost_audit_sha256','published_at_utc','calendar','minimum_hold_seconds',
        'maximum_target_age_seconds','maximum_metadata_age_seconds','cash_currency',
        'cash_policy','cost_policy','stop_policy','decision_policy','precedence',
        'research_only','production_activation','orders','real_capital'}
PRECEDENCE=['CALENDAR','MINIMUM_HOLD','EXACT_TARGET_REBALANCE']


def _state_fields(state):
    return dict(protocol_sha256=state.protocol_sha256,cash=str(state.cash),
        positions=[[a,str(q)] for a,q in state.positions],as_of_utc=state.as_of_utc,
        event_ids=list(state.event_ids),total_fees=str(state.total_fees),
        total_slippage=str(state.total_slippage))


def validate(raw,expected_sha256,available_at_utc,protocol,admission,cost_audit):
    book.check_hash(expected_sha256)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('mandate bytes changed')
    policy=intake.parse_json(raw)
    if not isinstance(policy,dict) or set(policy)!=FIELDS or policy.get('schema')!=SCHEMA:
        raise ValueError('complete exact-target mandate schema required')
    profile=policy['profile'];intake.spot_weights(admission,profile)
    if profile not in intake.SPOT:raise ValueError('spot profile required')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',policy['mandate_id']):raise ValueError('invalid mandate id')
    if (policy['research_only'] is not True or policy['production_activation'] is not False
            or type(policy['orders']) is not int or policy['orders']!=0
            or type(policy['real_capital']) is not int or policy['real_capital']!=0):
        raise ValueError('research boundary required')
    if (policy['protocol_sha256']!=protocol.sha256 or
            policy['target_admission_sha256']!=admission['admission_sha256'] or
            policy['cost_audit_sha256']!=cost_audit.get('cost_audit_sha256') or
            cost_audit.get('target_admission_sha256')!=admission['admission_sha256']):
        raise ValueError('mandate protocol/target/cost binding changed')
    if protocol.protocol_id!='GATE_BTC_DYNAMICS_SPOT_'+profile+'_V1':raise ValueError('profile/protocol mismatch')
    # Literal USDT only. No implicit USD conversion, interest, staking or credit.
    if policy['cash_currency']!=protocol.base_currency or protocol.base_currency!='USDT':
        raise ValueError('literal USDT cash policy required; no USD equivalence')
    if (policy['cash_policy']!='NONINTEREST_BEARING_NO_FX_NO_BORROWING' or
            policy['cost_policy']!='PER_FILL_SOURCE_FEE_SLIPPAGE_NO_EXTRA_DAILY_DRAG' or
            policy['stop_policy']!='NO_STOP_IN_THIS_EXPLICIT_MANDATE' or
            policy['decision_policy']!='PREAUTHORIZED_EXACT_TARGET_ONLY' or
            policy['precedence']!=PRECEDENCE):
        raise ValueError('unsupported policy semantics; no strategy inference')
    bound=costs.bind_cost_assumptions(protocol.instruments,cost_audit,profile)
    if bound!=protocol.instruments:raise ValueError('protocol costs do not match audited source assumptions')
    publication=book.timestamp(available_at_utc)
    if publication!=book.timestamp(policy['published_at_utc']):raise ValueError('mandate availability mismatch')
    activation=book.timestamp(protocol.activation_at_utc)
    if not activation<=book.timestamp(admission['source_available_at_utc'])<=publication:
        raise ValueError('mandate must follow source within the independent protocol epoch')
    for key in ['minimum_hold_seconds','maximum_target_age_seconds','maximum_metadata_age_seconds']:
        value=policy[key]
        if type(value) is not int or value<(0 if key=='minimum_hold_seconds' else 1):
            raise ValueError('explicit integer duration required: '+key)
    calendar=policy['calendar']
    if not isinstance(calendar,list) or not calendar:raise ValueError('explicit nonempty UTC calendar required')
    seen=set();last_close=None
    for slot in calendar:
        if not isinstance(slot,dict) or set(slot)!={'slot_id','opens_at_utc','closes_at_utc'}:
            raise ValueError('exact calendar slot required')
        name=slot['slot_id']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',name) or name in seen:
            raise ValueError('duplicate or invalid slot id')
        start,end=book.timestamp(slot['opens_at_utc']),book.timestamp(slot['closes_at_utc'])
        if not activation<=start<end or not publication<start or (last_close is not None and start<last_close):
            raise ValueError('calendar must be prospective, ordered and nonoverlapping')
        seen.add(name);last_close=end
    return policy


def rebalance_mandated(state,protocol,admission,audit,cost_audit,*,mandate_raw,
                       expected_mandate_sha256,mandate_available_at_utc,slot_id,
                       quotes,notional_references,executed_at_utc,previous_receipt=None):
    """Enforce the mandate, then atomically simulate one exact target rebalance.

    This intentionally supports no stop/hold override or inferred trigger.
    A different policy or target cannot be spliced onto this chain. A changed
    strategy must use a separately admitted independent protocol/series.
    """
    book.require_protocol(state,protocol)
    policy=validate(mandate_raw,expected_mandate_sha256,mandate_available_at_utc,
                    protocol,admission,cost_audit)
    execution=book.timestamp(executed_at_utc)
    slots=[s for s in policy['calendar'] if s['slot_id']==slot_id]
    if len(slots)!=1:raise ValueError('execution slot not preregistered')
    slot=slots[0]
    if not book.timestamp(slot['opens_at_utc'])<=execution<book.timestamp(slot['closes_at_utc']):
        raise ValueError('outside half-open execution window')
    age=(execution-book.timestamp(admission['source_available_at_utc'])).total_seconds()
    if not 0<=age<=policy['maximum_target_age_seconds']:raise ValueError('target outside mandate freshness')
    used=[];last=None
    if previous_receipt is None:
        initial=book.genesis(protocol)
        if state!=initial:raise ValueError('non-genesis state requires last mandated receipt')
    else:
        payload={k:v for k,v in previous_receipt.items() if k!='chain_sha256'}
        seal=book.digest(payload)
        if (seal!=previous_receipt.get('chain_sha256') or state.chain_sha256!=seal
                or previous_receipt.get('event')!='MANDATED_REBALANCE_RESEARCH_SEAL'
                or previous_receipt.get('mandate_sha256')!=expected_mandate_sha256
                or previous_receipt.get('state_after')!=_state_fields(state)):
            raise ValueError('last mandated receipt/state/policy chain mismatch')
        used=list(previous_receipt['used_slot_ids']);last=book.timestamp(previous_receipt['executed_at_utc'])
    if slot_id in used:raise ValueError('execution slot already consumed')
    if last is not None and (execution-last).total_seconds()<policy['minimum_hold_seconds']:
        raise ValueError('minimum hold has not elapsed')
    next_state,receipt=market.rebalance_market_checked(state,protocol,admission,policy['profile'],audit,
        rebalance_id=policy['mandate_id']+'.'+slot_id,quotes=quotes,
        notional_references=notional_references,executed_at_utc=executed_at_utc,
        max_metadata_age_seconds=policy['maximum_metadata_age_seconds'])
    event='MANDATE:'+policy['mandate_id']+':'+slot_id
    next_state=replace(next_state,event_ids=next_state.event_ids+(event,))
    result=dict(event='MANDATED_REBALANCE_RESEARCH_SEAL',mandate_sha256=expected_mandate_sha256,
        mandate_available_at_utc=mandate_available_at_utc,slot=slot,used_slot_ids=used+[slot_id],
        executed_at_utc=executed_at_utc,previous_state_chain_sha256=state.chain_sha256,
        protocol_sha256=protocol.sha256,target_admission_sha256=admission['admission_sha256'],
        cost_audit_sha256=cost_audit['cost_audit_sha256'],state_after=_state_fields(next_state),
        checked_rebalance=receipt,scientific_credit=0,economic_observations_created=0,
        production_activation=False,orders=0,real_capital=0)
    seal=book.digest(result)
    return replace(next_state,chain_sha256=seal),dict(result,chain_sha256=seal)
