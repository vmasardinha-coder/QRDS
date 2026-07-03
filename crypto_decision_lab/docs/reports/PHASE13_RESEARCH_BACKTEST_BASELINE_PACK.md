# QRDS/QOS Phase 13 Research Backtest Baseline Pack

Sprint 13A–13H builds the first statistical baseline from certified public OHLCV data.

It computes:

- rows and date span by symbol;
- cumulative return;
- hourly mean return;
- hourly and annualized volatility;
- positive-return rate;
- max drawdown;
- return percentiles;
- lag-1 autocorrelation;
- descriptive volatility and drawdown buckets.

Safety constraints:

- no trading signal;
- no recommendation;
- no allocation;
- no portfolio decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase13_research_backtest_baseline_pack_serve.sh
```
