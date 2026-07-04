# QRDS/QOS Phase 15 Multi-source Trust Registry + Comparison Pack

Sprint 15A–15P consolidates source readiness and compares certified public sources.

Sources:

- Binance Spot public klines;
- Hyperliquid public perps candles;
- OKX public swap candles;
- Bybit public linear klines, allowed as pending if blocked/unavailable.

Outputs:

- source trust registry;
- ready/pending source classification;
- pairwise price spread and return-correlation comparisons;
- safety and non-operational report.

Safety constraints:

- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase15_multisource_trust_registry_comparison_pack_serve.sh
```
