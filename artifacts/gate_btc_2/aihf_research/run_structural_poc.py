# RESEARCH_ONLY=true
# SHADOW_ONLY=true
from __future__ import annotations

import json
from pathlib import Path

from hedge_fund.models import Signal
from hedge_fund.portfolio.construction import blend_signals
from hedge_fund.risk.limits import RiskLimits, apply_limits

OUT=Path('artifacts/gate_btc_2/aihf_research/runtime_structural')
OUT.mkdir(parents=True, exist_ok=True)
DATE='2026-01-02'

def sig(model,ticker,value,abstained=False):
    return Signal(model_name=model,ticker=ticker,date=DATE,value=value,metadata={'abstained':abstained})

weights={'m1':1.0,'m2':1.0}
# Same bullish model, second model changes only information state.
case_abstain=blend_signals([sig('m1','BTC',1.0),sig('m2','BTC',0.0,True)],weights,1.0)
case_neutral=blend_signals([sig('m1','BTC',1.0),sig('m2','BTC',0.0,False)],weights,1.0)
case_all_abstain=blend_signals([sig('m1','BTC',0.0,True),sig('m2','BTC',0.0,True)],weights,1.0)

assert case_abstain.convictions['BTC'] == 1.0
assert case_neutral.convictions['BTC'] == 0.5
assert case_all_abstain.convictions['BTC'] == 0.0
assert case_all_abstain.weights['BTC'] == 0.0

# Net-book risk: proposed book is deliberately over limits; risk may only shrink magnitude.
proposed={'BTC':0.8,'ETH':0.6,'SOL':-0.4}
limits=RiskLimits(max_position_pct=0.5,max_gross_exposure=0.9)
risk=apply_limits(proposed,limits)
assert sum(abs(v) for v in risk.weights.values()) <= 0.9000000001
assert all(abs(risk.weights[t]) <= min(abs(proposed[t]),0.5)+1e-12 for t in proposed)
assert len(risk.clamps) >= 1

# Cross-sectional market-neutral behavior is deterministic and exactly zero-sum within float tolerance.
mn=blend_signals([
    sig('m1','BTC',1.0),sig('m1','ETH',0.2),sig('m1','SOL',-0.4),
],{'m1':1.0},1.0,market_neutral=True)
assert abs(sum(mn.weights.values())) < 1e-12
assert abs(sum(abs(v) for v in mn.weights.values())-1.0) < 1e-12

result={
  'research_only':True,
  'shadow_only':True,
  'factory_modified':False,
  'upstream_sha':'154a8b2f46dca0f40764d814e4e747b0ad71f4c4',
  'upstream_version':'2.3.0',
  'alpha_tested':False,
  'api_dependent_behavior_tested':False,
  'abstain_vs_neutral':{
      'bull_plus_abstain_conviction':case_abstain.convictions['BTC'],
      'bull_plus_neutral_conviction':case_neutral.convictions['BTC'],
      'all_abstain_conviction':case_all_abstain.convictions['BTC'],
      'all_abstain_weight':case_all_abstain.weights['BTC'],
  },
  'risk_after_proposal':{
      'proposed':proposed,
      'final':risk.weights,
      'proposed_gross':sum(abs(v) for v in proposed.values()),
      'final_gross':sum(abs(v) for v in risk.weights.values()),
      'clamps':[c.model_dump() for c in risk.clamps],
  },
  'market_neutral':{'weights':mn.weights,'net':sum(mn.weights.values()),'gross':sum(abs(v) for v in mn.weights.values())},
  'interpretation':'Abstention is semantically distinct from an explicit neutral vote; hard risk limits only reduce proposed exposure; both behaviors are deterministic correctness properties, not alpha claims.'
}
(OUT/'structural_poc.json').write_text(json.dumps(result,indent=2,sort_keys=True))
print(json.dumps(result,indent=2,sort_keys=True))
