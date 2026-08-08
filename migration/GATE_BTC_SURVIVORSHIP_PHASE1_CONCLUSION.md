# GATE BTC — Survivorship Phase 1 Conclusion

Status: **CLOSED AS RESEARCH EVIDENCE / NOT APPROVED FOR OPERATION**  
Canonical evidence run: **31276127634 (#115)**  
Artifact: `gate-btc-survivorship-definitive-31276127634`  
Artifact id: `9027220602`  
Artifact SHA-256: `e3b484f8797685547b7e59aa86f19e9080daaac551b1488b6ea0fac9f8fd5f81`

## Frozen question

After reconstructing the historical CoinMarketCap Top-150 point-in-time universe and removing survivorship bias, do QOS Moderada / Ultra demonstrate structural selection alpha over the contemporaneous unfiltered PIT basket and BTC under strict next-bar execution?

## Final clean coverage state

Run #115 adds two identity corrections without changing the frozen strategy methodology:

1. bounded pre-genesis `DYDXERC20` history, with no native/legacy stitching;
2. exact unresolved historical CMC slug -> unique rank-sorted active CMC ticker recovery, with no name fallback, no overwrite and conflict/ambiguity fail-closed.

Results:

- 74 historical month-end Top-150 snapshots;
- 576 unique PIT symbols after identity segmentation;
- 444 identity/history-usable symbols;
- 235 previously unresolved snapshot rows recovered by exact CMC slug;
- signal coverage mean: **95.8095%**;
- signal coverage max: **100%**;
- signals >=95%: **63/74**;
- weekly minimum-coverage weeks >=95%: **203/319**;
- strict common alpha sample: **201 weeks**;
- every month from **2021-06-30 through 2026-07-31** passes the 95% signal gate.

The 11 sub-95% signal months are all in 2020 through May 2021. The remaining early tail is dominated by legacy/migration/identity cases for which the source cascade did not produce admissible exact history (examples include BORG, REV, BTCB, BCD, ABBC and VLX). BORG/CHSB remains hard-blocked, BTCB may not proxy BTC, and AMPL price-only recovery remains prohibited.

## Alpha result

On the 201-week strict PIT sample:

- `UNFILTERED_PIT` alpha vs BTC: **-0.77196%/week**;
- `SELECTED_MODERADA_PIT` alpha vs BTC: **-1.02493%/week**;
- Moderada incremental alpha vs unfiltered: **-0.25296%/week**;
- `SELECTED_ULTRA_PIT` alpha vs BTC: **-0.93141%/week**;
- Ultra incremental alpha vs unfiltered: **-0.15944%/week**.

The direct incremental-alpha HAC 95% intervals cross zero for both selected variants, so the evidence does not support positive structural selection alpha.

Regime decomposition is directionally important:

- DEFENSIVE: selection delta vs unfiltered is approximately **-0.6462%/week** (Moderada) and **-0.5611%/week** (Ultra);
- RISK_ON: selection delta is approximately **+0.0738%/week** (Moderada) and **+0.1755%/week** (Ultra).

The small RISK_ON advantage is not sufficient to overcome the DEFENSIVE damage in the aggregate and is not treated as an approved regime rule.

## Scientific conclusion

**Structural positive alpha from the current QOS selection layer is not demonstrated after the survivorship correction.** Improving clean PIT coverage from the earlier baselines to #115 did not recover positive aggregate selection alpha. The result therefore should not be explained away as a modern-identity coverage artifact.

This is a useful negative result: the next research question is no longer “can missing historical members rescue the selector?” but “does the selector identify temporary winners whose gains are lost because the holding/exit rule is poor?”

## Phase-1 stopping rule

Phase 1 stops here rather than weakening identity or source standards to force 100% coverage. Further legacy recovery is allowed only as future evidence maintenance and may not be used to revise this conclusion opportunistically.

No strategy, source chain, production input, order path, capital allocation or operational approval is changed by this conclusion.

Safety: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED`, `ENGINE_FEED=false`, orders=0, capital=0, Phase-1 methodology changes=0.
