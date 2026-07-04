# QRDS/QOS Phase 16 Multi-source Consensus Baseline Pack

Sprint 16A–16R builds an artifact-only consensus baseline from certified public sources.

Inputs:

- Phase 15 trust registry and comparison;
- Binance Spot public candles;
- Hyperliquid public perps candles;
- OKX public swap candles;
- Bybit remains excluded while pending.

Outputs:

- per-coin consensus CSVs in the Phase 16 artifact directory;
- consensus close median and mean;
- source dispersion in basis points;
- source deviations from consensus;
- research-only volatility summaries;
- visual report.

Safety constraints:

- artifact outputs only;
- no canonical promotion;
- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase16_multisource_consensus_baseline_pack_serve.sh
```
