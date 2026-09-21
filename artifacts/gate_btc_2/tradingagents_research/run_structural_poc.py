# RESEARCH_ONLY=true
# SHADOW_ONLY=true
from __future__ import annotations

import json
from pathlib import Path

from tradingagents.agents.schemas import PortfolioDecision, PortfolioRating, ResearchPlan, TraderAction, TraderProposal
from tradingagents.agents.utils.agent_states import InvestDebateState, RiskDebateState

OUT = Path('artifacts/gate_btc_2/tradingagents_research/runtime_structural')
OUT.mkdir(parents=True, exist_ok=True)

RATING_SCORE = {
    PortfolioRating.BUY: 2,
    PortfolioRating.OVERWEIGHT: 1,
    PortfolioRating.HOLD: 0,
    PortfolioRating.UNDERWEIGHT: -1,
    PortfolioRating.SELL: -2,
}
ACTION_SCORE = {TraderAction.BUY: 1, TraderAction.HOLD: 0, TraderAction.SELL: -1}


def handoff_disagreement(research: ResearchPlan, trader: TraderProposal, pm: PortfolioDecision) -> dict:
    rs = RATING_SCORE[research.recommendation]
    ts = ACTION_SCORE[trader.action] * 2
    ps = RATING_SCORE[pm.rating]
    spread = max(rs, ts, ps) - min(rs, ts, ps)
    direction_flip = (rs > 0 and ps < 0) or (rs < 0 and ps > 0)
    trader_flip = (rs > 0 and ts < 0) or (rs < 0 and ts > 0)
    return {
        'research_score': rs,
        'trader_score_scaled': ts,
        'portfolio_score': ps,
        'ordinal_spread': spread,
        'direction_flip_research_to_pm': direction_flip,
        'direction_flip_research_to_trader': trader_flip,
        'high_disagreement': bool(spread >= 3 or direction_flip or trader_flip),
    }

# Frozen synthetic hand-offs. These are structural tests, not market evidence.
scenarios = [
    (
        'aligned_bullish',
        ResearchPlan(recommendation='Buy', rationale='bull case', strategic_actions='size normally'),
        TraderProposal(action='Buy', reasoning='aligned'),
        PortfolioDecision(rating='Buy', executive_summary='aligned', investment_thesis='aligned'),
    ),
    (
        'moderate_softening',
        ResearchPlan(recommendation='Buy', rationale='bull case', strategic_actions='size normally'),
        TraderProposal(action='Hold', reasoning='execution caution'),
        PortfolioDecision(rating='Overweight', executive_summary='reduced conviction', investment_thesis='still positive'),
    ),
    (
        'risk_veto',
        ResearchPlan(recommendation='Buy', rationale='bull case', strategic_actions='buy'),
        TraderProposal(action='Buy', reasoning='buy proposal'),
        PortfolioDecision(rating='Sell', executive_summary='risk veto', investment_thesis='risk dominates'),
    ),
    (
        'aligned_bearish',
        ResearchPlan(recommendation='Sell', rationale='bear case', strategic_actions='reduce'),
        TraderProposal(action='Sell', reasoning='aligned'),
        PortfolioDecision(rating='Sell', executive_summary='aligned', investment_thesis='aligned'),
    ),
]

rows=[]
for name,r,t,p in scenarios:
    rows.append({'scenario':name, **handoff_disagreement(r,t,p)})

# Verify independent debate channels are present in the upstream state contract.
invest_keys=set(InvestDebateState.__annotations__)
risk_keys=set(RiskDebateState.__annotations__)
required_invest={'bull_history','bear_history','judge_decision','count'}
required_risk={'aggressive_history','conservative_history','neutral_history','judge_decision','count'}
assert required_invest <= invest_keys
assert required_risk <= risk_keys
assert rows[0]['high_disagreement'] is False
assert rows[2]['high_disagreement'] is True and rows[2]['direction_flip_research_to_pm'] is True

result={
    'research_only': True,
    'shadow_only': True,
    'factory_modified': False,
    'upstream_sha': '2d17df8da1536c121e4d7395ac5a5dcec9e96d6f',
    'upstream_version': '0.5.0',
    'poc_type': 'deterministic structured handoff disagreement audit',
    'market_alpha_tested': False,
    'llm_provider_behavior_tested': False,
    'independent_bull_bear_channels_present': True,
    'independent_risk_stance_channels_present': True,
    'rows': rows,
    'interpretation': 'The upstream structured decision pipeline supports a deterministic disagreement audit across research/trader/portfolio handoffs. This proves auditability of disagreement, not predictive value.',
    'migration_boundary': 'Do not migrate as alpha until disagreement is tested against point-in-time outcomes. Candidate methodology only.',
}
(OUT/'structural_poc.json').write_text(json.dumps(result,indent=2,sort_keys=True))
print(json.dumps(result,indent=2,sort_keys=True))
