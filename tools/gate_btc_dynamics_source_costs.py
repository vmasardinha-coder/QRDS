"""Bind frozen producer cost assumptions without scheduling or activation.

The archive and admitted CSV are explicit byte authorities. Never execute
Python from the archive or confuse estimated daily drag with per-fill fees.
"""
from __future__ import annotations
import ast,hashlib,io,zipfile
from dataclasses import replace
from decimal import Decimal
from tools import gate_btc_dynamics_spot_accounting as book
from tools import gate_btc_dynamics_target_intake as intake

SCRIPT='scripts/00_run_all_v2a1.py'
CONSTANTS=('EST_FEE_BPS_PER_SIDE','EST_SLIPPAGE_BPS_PER_SIDE','EST_SHORT_FUNDING_BPS_PER_DAY')


def audit_costs(source_archive:bytes,expected_archive_sha256:str,profiles_raw:bytes,admission:dict)->dict:
    book.check_hash(expected_archive_sha256)
    if hashlib.sha256(source_archive).hexdigest()!=expected_archive_sha256:
        raise ValueError('canonical source archive hash mismatch')
    for profile in intake.SPOT:intake.spot_weights(admission,profile)
    if hashlib.sha256(profiles_raw).hexdigest()!=admission['source_hashes']['strategy_execution_profiles.csv']:
        raise ValueError('cost CSV is not the admitted source')
    with zipfile.ZipFile(io.BytesIO(source_archive)) as archive:
        if archive.namelist().count(SCRIPT)!=1:raise ValueError('missing or duplicate canonical producer')
        raw=archive.read(SCRIPT)
    values={}
    for node in ast.parse(raw.decode('utf-8-sig')).body:
        if not isinstance(node,ast.Assign):continue
        for target in node.targets:
            if not isinstance(target,ast.Name) or target.id not in CONSTANTS:continue
            if target.id in values:raise ValueError('duplicate cost constant')
            if not isinstance(node.value,ast.Constant) or type(node.value.value) not in (int,float):
                raise ValueError('cost constants must be literal numbers')
            value=book.number(str(node.value.value))
            if not 0<=value<10000:raise ValueError('invalid source cost rate')
            values[target.id]=value
    if set(values)!=set(CONSTANTS):raise ValueError('missing source cost constant')
    required=['strategy','estimated_daily_turnover','estimated_trading_cost_bps_per_day',
              'estimated_short_funding_bps_per_day','estimated_total_drag_bps_per_day',
              'stop_rules_backtested','walk_forward_backtested','recommended_rebalance']
    rows=intake.table(profiles_raw,required);by_name={}
    for row in rows:
        if row['strategy'] in by_name:raise ValueError('duplicate cost profile')
        by_name[row['strategy']]=row
    if set(by_name)!=set(admission['profiles']):raise ValueError('cost profile cohort mismatch')
    result_profiles={}
    for name in sorted(intake.SPOT):
        row=by_name[name];profile=admission['profiles'][name]
        turnover=book.number(row['estimated_daily_turnover'])
        if not 0<=turnover<=1:raise ValueError('invalid assumed turnover')
        expected=turnover*(values[CONSTANTS[0]]+values[CONSTANTS[1]])*2
        trading,funding,total=[book.number(row[k]) for k in required[2:5]]
        if (abs(trading-expected)>Decimal('1e-12') or funding!=0
                or abs(total-trading-funding)>Decimal('1e-12')):
            raise ValueError('source daily drag does not reconcile')
        if row['recommended_rebalance']!=profile['recommended_rebalance']:
            raise ValueError('source rebalance label changed')
        if any(row[k]!='False' for k in ['stop_rules_backtested','walk_forward_backtested']):
            raise ValueError('unexpected backtest claim; new source review required')
        result_profiles[name]=dict(assumed_daily_turnover=str(turnover),
            estimated_daily_trading_drag_bps=str(trading),fee_bps_per_side=str(values[CONSTANTS[0]]),
            slippage_bps_per_side=str(values[CONSTANTS[1]]),recommended_rebalance=row['recommended_rebalance'])
    result=dict(schema='gate_btc.dynamics_source_cost_assumptions.v1',
        status='SOURCE_ASSUMPTIONS_VERIFIED_NOT_EXECUTION_POLICY',
        source_archive_sha256=expected_archive_sha256,source_script_sha256=hashlib.sha256(raw).hexdigest(),
        target_admission_sha256=admission['admission_sha256'],
        source_profiles_sha256=hashlib.sha256(profiles_raw).hexdigest(),profiles=result_profiles,
        daily_drag_is_not_per_fill_fee=True,observed_exchange_fees_verified=False,
        cash_currency_bound=False,executable_calendar_defined=False,hold_stop_precedence_defined=False,
        production_activation=False,economic_observations_created=0,orders=0,real_capital=0)
    return dict(result,cost_audit_sha256=book.digest(result))


def bind_cost_assumptions(instruments:tuple,audit:dict,profile:str)->tuple:
    """Return inactive instrument bindings, without creating a protocol or NAV."""
    payload={k:v for k,v in audit.items() if k!='cost_audit_sha256'}
    if book.digest(payload)!=audit.get('cost_audit_sha256'):raise ValueError('cost audit changed')
    if audit.get('schema')!='gate_btc.dynamics_source_cost_assumptions.v1':raise ValueError('unsupported cost audit')
    if profile not in intake.SPOT or profile not in audit['profiles']:
        raise ValueError('only the three admitted spot profiles are supported')
    if not isinstance(instruments,tuple) or not instruments:raise ValueError('explicit nonempty immutable bindings required')
    if len({i.asset for i in instruments})!=len(instruments):raise ValueError('duplicate instrument')
    for i in instruments:
        if i.instrument_type!='SPOT' or i.asset in {'CASH','USD','USDT','USDC'}:
            raise ValueError('only unlevered asset spot bindings supported')
        if (i.venue!='BINANCE' or i.quote_currency!='USDT' or i.market!=i.asset+'USDT'
                or i.exact_identity!='BINANCE:SPOT:'+i.market):
            raise ValueError('audited Binance USDT identity required; no USD equivalence')
    item=audit['profiles'][profile]
    return tuple(replace(i,fee_bps_per_side=item['fee_bps_per_side'],
        slippage_bps_per_side=item['slippage_bps_per_side']) for i in instruments)
