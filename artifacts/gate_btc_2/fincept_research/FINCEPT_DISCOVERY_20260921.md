# Fincept Terminal isolated discovery — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Upstream: `Fincept-Corporation/FinceptTerminal`  
Pinned SHA: `b7d850b49dc033bb133e6e5d2476444ac5c422b1`  
Open-source release line: `v4.5.0`

## Research question
Determine whether Fincept Terminal contributes a reproducible research hypothesis, validation method, or source/materialization capability to GATE BTC 2.0 beyond what is already present.

## Initial focus
The repository is primarily a broad desktop terminal. We do not treat breadth, UI, provider count, or marketing claims as value by themselves. The first bounded test targets the standalone Python factor-evaluation module used by AI Quant Lab because it can be evaluated deterministically without LLM/provider credentials.

Upstream module: `fincept-qt/scripts/ai_quant_lab/qlib_evaluation.py`.

## Frozen tests
1. A constructed cross-sectional factor with known predictive ordering must show strong positive Pearson and Spearman IC.
2. A deterministic shuffled/noise factor must not be confused with the known factor.
3. Quantile analysis must preserve the expected monotonic ordering under a frozen return construction.
4. Turnover semantics are audited against a hand-computed top-N overlap definition.

## Boundaries
- No external Fincept performance claim is imported.
- No Qlib-trained model is accepted as alpha without independent PIT testing.
- No LLM agent output is used.
- No proprietary Enterprise/Quantcept source is used.
- Factory remains untouched during isolated research.
- A metric-definition bug or duplicate methodology is not migrated merely because it exists upstream.
