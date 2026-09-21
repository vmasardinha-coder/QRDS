# XRP/BTC regime-gate — isolated research conclusion

Date: 2026-09-21

Status: **KEEP FOR EXTERNAL RESEARCH / SHADOW ONLY**

This conclusion is intentionally isolated from the active QRDS Factory.

Safety boundary:
- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- no live orders
- no capital
- no registration/promotion into `artifacts/gate_btc_2/factory/`
- no Factory workflow modified

## Hypothesis

A higher-timeframe BTC regime may condition the quality of XRP trend-entry signals.

Exact confirmatory rule:
- traded asset: XRP/USDT
- entry timeframe: 1h
- base entry: fresh EMA20 cross above EMA50
- regime gate: BTC/USDT 12h close > BTC 12h SMA20
- exit: fixed 48h time exit
- exchange/data: OKX
- execution auditor: Freqtrade
- explicit fee: 0.10% per side (~0.20% round trip)
- no parameter retuning between confirmatory research and Freqtrade audit

## Deep isolated research

On the aligned 8000-row XRP/BTC 1h sample (2025-10-23 through 2026-09-21), the 48h ungated base signal was negative while the BTC 12h/SMA20 gate was positive.

At 0.20% round-trip cost:
- ungated base: 63 trades, mean about -0.72% per event, total compounded result about -40%, PF about 0.63
- gated 12h/SMA20: 29 trades, mean about +0.53% per event, total compounded result about +10.8%, PF about 1.33, max drawdown about -9.5%
- walk-forward incremental delta was positive in 4/5 evaluation windows

The sample remains small, so this is evidence for continued research, not promotion.

## Freqtrade exact execution audit

Same engine, same timerange, same exchange, same market-order semantics, same 48h exit, same fee configuration.

| Metric | Ungated XRP EMA20/50 | BTC 12h/SMA20 gated | Incremental effect |
|---|---:|---:|---:|
| Trades | 63 | 29 | -34 trades |
| Avg profit/trade | -0.66% | +0.42% | **+1.08 pp** |
| Absolute profit | -413.153 USDT | +121.694 USDT | **+534.847 USDT** |
| Account return | -4.13% | +1.22% | **+5.35 pp** |
| Profit factor | 0.67 | 1.22 | **+0.55** |
| Closed-trade Sharpe | -0.54 | +0.11 | **+0.65** |
| Closed-trade Sortino | -0.87 | +0.29 | **+1.16** |
| Max account underwater | 5.10% | 2.03% | **-3.07 pp** |
| Wins / losses | 23 / 40 | 11 / 18 | lower N, similar hit rate |

The market itself changed about -39.77% over the same engine timerange.

## Bias audit

Freqtrade lookahead analysis on the gated strategy:
- `has_bias = No`
- total signals checked: 20
- biased entry signals: 0
- biased exit signals: 0

## Scientific interpretation

The useful object is **not** the XRP EMA crossover by itself. The baseline is demonstrably negative under the same execution engine. The value observed in this experiment comes from conditioning entries on the higher-timeframe BTC regime.

This is therefore a genuine incremental-filter result in this bounded sample, not merely a profitable standalone rule.

However, it is **not yet a survivor suitable for Factory promotion** because:
1. only 29 gated trades occurred in the exact Freqtrade audit;
2. the evidence covers one traded asset and one bounded historical period;
3. the selected gate emerged from a small candidate set examined during research;
4. forward/shadow evidence has not accumulated yet.

## Disposition

**KEEP — external research/shadow candidate.**

Do not integrate into the active Factory now.

Next scientific work, still isolated:
1. replicate the same fixed gate on additional altcoins without retuning;
2. test older/non-overlapping historical periods if available from a compatible PIT source;
3. preserve the exact 12h/SMA20/48h rule while accumulating forward shadow evidence;
4. reject if cross-asset replication or forward evidence does not support the incremental effect.

## Related negative result

The previously promising SOL multi-horizon MA lattice was downgraded after deeper non-overlapping executable tests. Its initial apparent edge did not survive stricter trade semantics; the only marginal surviving variant had PF near 1.08, weak walk-forward consistency, and roughly 33% drawdown. It should not advance to Factory or execution audit at this stage.
