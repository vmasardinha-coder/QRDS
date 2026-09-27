# M1/M2 — technical repair and required scientific disposition

## Verified current problem

The canonical economic STATE/HISTORY stop at 2026-09-13. LSK is held in both
strategies, but the dynamic current V2A universe no longer supplies its price.
A live same-provider check on 2026-09-27 observed the completed 2026-09-26 LSK
close at 0.3408 in both CDD's Binance file and Binance's official candles.
The provider is alive. The economic collector omitted a held identity.

The old workflow swallowed PRICE_MISSING_LSK through continue-on-error and
reported success without publication. It uploaded no economic source artifact.
Persisted signal snapshots exist for 14 and 26 September, but they contain ranks,
metrics and price-master hashes, not the missing economic input bytes. A hash
alone cannot recover those bytes or establish a retrospective economic series.
No sufficient causal economic source archive was identified in the audited
Momentum runtime/workflow. This is not a claim that every external archive has
been exhaustively searched; backfill remains unauthorized regardless.

## Delivered mechanical repair

A dedicated collector requests the union of held identities, frozen current
Top10 selections and BTC. It reuses canonical CDD/Binance source loaders and
archives exact responses, actual receipt timestamps, the selected current-close
prices and hashes. It never changes M1/M2 rankings, global V2A inputs or history.
Only the latest completed UTC close is admissible. Source failures are explicit;
immutable same-cutoff evidence is reused. OKX's legacy `1D` fallback is not used
here because its daily alignment is not qualified as the required UTC boundary.

The workflow serializes economic writes, verifies original STATE/HISTORY hashes,
publishes source/delivery diagnostics even when the economic step is blocked,
and returns failure after preserving evidence. Main reporting distinguishes
fresh signals, current price coverage and the last actual economic mark.

## Two scientific problems remain; no silent repair

1. The historical series already skips 2026-09-05 and 2026-09-11. The next requested
   cutoff is 2026-09-26, following the last mark on 13 September. Advancing once
   would incorrectly treat multiple closes as one weekly-cadence observation.
2. The contract says equal weighting at seven-close rebalances and HOLD in
   between. The engine averages asset returns with equal weights every day,
   implicitly rebalancing daily. A two-asset example, prices (100,100) ->
   (200,100) -> (100,100), ends at 0% under HOLD but +12.5% under the old arithmetic.

Existing economic files and P&L remain unchanged, with gross-only costs N_D.
They are historical diagnostics, not a continuous validated live performance
series. The repaired runner blocks rather than manufacturing continuity or
silently changing the engine. The original arithmetic is preserved in Git at
94f3206cf250296ea2077f8836de7967b6aca590:tools/gate_btc_momentum_economic_shadow.py.

## Concrete proposed disposition — NOT APPROVED

- Close the interrupted economic epoch as a preserved diagnostic, with its
  original files/hashes/rows and explicit gaps. Do not reset or overwrite it.
- Repair future accounting to hold fixed quantities between the frozen weekly
  rebalances; equal weight only at activation/rebalance. Preserve the M1/M2
  score formulas, Top10 selections, seven completed UTC closes, BTC benchmark,
  shadow close execution and gross-only N_D cost policy.
- Begin a separate prospective economic epoch after approval, with independent
  initial NAV 1 and no inherited P&L, counters or retrospective observations.
  Continue signal collection unchanged. Report daily gross economics separately.
- Do not assign D100's N80 to M1/M2: its current contract does not define that
  terminal gate, promotion or net-performance certification.

Victor's standing operating boundary reserves scientific/engine/clock changes
for explicit decision. Approval of this disposition permits implementing/testing
that exact new epoch; it does not claim it is already active.
