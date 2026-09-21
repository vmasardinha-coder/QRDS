# RESEARCH_ONLY=true
# SHADOW_ONLY=true
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

UPSTREAM = Path(os.environ.get('FINCEPT_EVAL_SCRIPT','/tmp/qlib_evaluation.py'))
spec=importlib.util.spec_from_file_location('fincept_qlib_evaluation',UPSTREAM)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
svc=mod.EvaluationService()

rng=np.random.default_rng(20260921)
dates=pd.date_range('2025-01-01',periods=60,freq='D')
assets=[f'A{i:02d}' for i in range(40)]
base=np.tile(np.linspace(-2,2,len(assets)),(len(dates),1))
# Small date-varying perturbation preserves cross-sectional ordering while avoiding constant rows.
factor=pd.DataFrame(base+rng.normal(0,0.05,base.shape),index=dates,columns=assets)
returns=pd.DataFrame(0.02*factor.values+rng.normal(0,0.005,base.shape),index=dates,columns=assets)
noise=pd.DataFrame(rng.normal(0,1,base.shape),index=dates,columns=assets)

known_ic=svc.calculate_ic_metrics(factor,returns,'pearson')
known_rank=svc.calculate_rank_ic(factor,returns)
noise_ic=svc.calculate_ic_metrics(noise,returns,'pearson')
quant=svc.analyze_factor_returns(factor,returns,quantiles=5)

# Hand-audited turnover fixture: top-2 names completely switch between two dates.
turn_fixture=pd.DataFrame(
    [[4,3,2,1],[1,2,3,4]],
    index=pd.to_datetime(['2025-01-01','2025-01-02']),columns=['A','B','C','D']
)
turn=svc.calculate_factor_turnover(turn_fixture,top_n=2)
# Standard one-way replacement turnover = 1 - overlap/N = 1.0 for disjoint sets.
manual_one_way=1.0
reported=float(turn['mean_turnover'])

assert known_ic['success'] and known_rank['success'] and noise_ic['success'] and quant['success'] and turn['success']
assert known_ic['IC_mean'] > 0.9
assert known_rank['IC_mean'] > 0.9
assert abs(noise_ic['IC_mean']) < 0.15
# Upstream Q1-Q5 orientation means increasing factor/return ordering yields a negative Q1-Q5 spread.
assert quant['spread'] < 0
assert abs(reported-2.0) < 1e-12

result={
  'research_only':True,'shadow_only':True,'factory_modified':False,
  'upstream_sha':'b7d850b49dc033bb133e6e5d2476444ac5c422b1',
  'module':'fincept-qt/scripts/ai_quant_lab/qlib_evaluation.py',
  'market_alpha_tested':False,
  'known_factor':{'pearson_ic_mean':known_ic['IC_mean'],'rank_ic_mean':known_rank['IC_mean'],'observations':known_ic['observations']},
  'noise_factor':{'pearson_ic_mean':noise_ic['IC_mean'],'observations':noise_ic['observations']},
  'quantile_analysis':{'spread_q1_minus_q5':quant['spread'],'long_short_sharpe_q1_minus_q5':quant['long_short_sharpe'],'monotonicity':quant['monotonicity']},
  'turnover_audit':{
      'fixture':'two disjoint top-2 sets',
      'upstream_reported_mean_turnover':reported,
      'standard_one_way_replacement_turnover':manual_one_way,
      'ratio_upstream_to_one_way':reported/manual_one_way,
      'definition_issue':'Upstream uses symmetric_difference/top_n, yielding range 0..2 while docstring describes percent of portfolio changed. This is twice the common one-way replacement rate for equal-size top-N sets.'
  },
  'interpretation':'IC/rank-IC and quantile ordering behave correctly on the frozen synthetic oracle. Turnover is internally deterministic but its documented percent-changed interpretation is doubled relative to the common one-way replacement definition. No alpha claim.'
}
out=Path('artifacts/gate_btc_2/fincept_research/runtime_factor_eval'); out.mkdir(parents=True,exist_ok=True)
(out/'factor_evaluation_result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
print(json.dumps(result,indent=2,sort_keys=True))
