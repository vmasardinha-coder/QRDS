# WIN/WDO frozen execution boundary — 2026-09-04

This branch executes only the 12 preregistered own-market families B3WIN01-B3WIN06 and B3WDO01-B3WDO06 under the already-merged official PriceReport source contract, accepted cost convention, and pre-economics normalization/gates.

The existing 20-quarter PriceReport coverage artifacts are enriched with exact WIN/WDO OHLCV rows plus report-leaf identity and reused directly by the executor. No second source, continuous-series construction, roll stitching, cross-asset input, H1/H31/BTC/DI/FX/macro read, threshold change, family change, direction change, hold change, cost change, cutoff change, PIT change, backfill, or counter reset is introduced.

The known 2021-06-10 single source gap remains excluded without reconstruction or credit. The workflow is the existing B3 factory workflow; no new workflow and no schedule are added. Any new source/transport failure remains fail-closed. NULL remains a valid scientific result.
