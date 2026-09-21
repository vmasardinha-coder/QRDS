# Hummingbot — Scientific Conclusion — 2026-09-21

## Scope

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- Factory untouched.
- No live capital, no production execution, no Factory survivor admission.

Hummingbot was evaluated as a source of orthogonal execution/microstructure ideas, with emphasis on pure market making inventory control and cross-exchange market making.

## 1. Pure market making inventory skew

Frozen causal OHLCV proxy:
- OKX BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT
- 5m, 8,000 bars per asset
- initial equity 10,000
- target base ratio 50%
- order value 1% of portfolio
- 20 bps spread per side
- 10 bps fee per fill
- quotes use previous closed bar; next bar is only used as a conservative fill proxy
- if both sides are touched inside the same OHLCV bar, both fills are skipped because event ordering is ambiguous

### Static PMM proxy vs inventory-skew overlay

| Asset | Static return | Skew return | Return delta | Static RMS inventory deviation | Skew RMS inventory deviation | Inventory RMS delta |
|---|---:|---:|---:|---:|---:|---:|
| BTC | -13.7841% | -14.0741% | -0.2900 pp | 32.9612% | 3.6133% | -29.3479 pp |
| ETH | +7.3413% | +7.4698% | +0.1285 pp | 12.6923% | 3.2847% | -9.4076 pp |
| SOL | -7.2446% | -12.2631% | -5.0184 pp | 24.1326% | 3.2032% | -20.9294 pp |
| XRP | -31.3425% | -29.9667% | +1.3757 pp | 12.1219% | 4.0278% | -8.0941 pp |

The overlay strongly reduced inventory drift in all four assets. Return impact was mixed and therefore is not evidence of standalone alpha.

### Classification

`pure_market_making_inventory_skew = KEEP_RESEARCH_RISK_OVERLAY`

Interpretation: useful inventory-risk control logic, not a proven alpha family. Before any migration it requires true L2/order-book replay or prospective shadow observation with queue/fill modeling.

## 2. Cross-exchange market making

A contemporaneous order-book probe was run on BTC/USDT using OKX, Bitget and Gate. Bybit was initially selected but was geo-blocked from the GitHub-hosted runner; it was replaced mechanically by Gate without changing economic assumptions.

Frozen probe:
- 20 snapshots
- 6 directional venue pairs per snapshot = 120 directional observations
- 1,000 USDT notional
- exact same base quantity bought and sold across venues
- depth-aware VWAP using up to 20 order-book levels
- frozen total friction = 25 bps:
  - maker fee 10 bps
  - taker fee 10 bps
  - latency haircut 5 bps

### Results

| Direction | Gross mean | Gross max | Net mean after 25 bps | Net max | Net-positive observations |
|---|---:|---:|---:|---:|---:|
| Bitget → Gate | +0.1011 bps | +0.9019 bps | -24.8989 bps | -24.0981 bps | 0/20 |
| Bitget → OKX | +0.1249 bps | +2.4990 bps | -24.8751 bps | -22.5010 bps | 0/20 |
| Gate → Bitget | -0.3842 bps | +1.4293 bps | -25.3842 bps | -23.5707 bps | 0/20 |
| Gate → OKX | -0.2581 bps | +2.3955 bps | -25.2581 bps | -22.6045 bps | 0/20 |
| OKX → Bitget | -0.1621 bps | +0.7528 bps | -25.1621 bps | -24.2472 bps | 0/20 |
| OKX → Gate | -0.0598 bps | +1.2045 bps | -25.0598 bps | -23.7955 bps | 0/20 |

Best observed gross spread was only +2.4990 bps, far below the frozen 25 bps friction. There were zero net-positive observations out of 120 directional venue/snapshot combinations.

### Classification

`cross_exchange_market_making = REJECT_AS_ALPHA_UNDER_FROZEN_FRICTION / NO_ADVANCE`

This is not a universal claim that cross-exchange market making can never work. It means this frozen economic version did not earn advancement in the observed sample and should not receive a parameter/fee retune based on this result.

## 3. Avellaneda-style / order-book-intensity market making

This class depends materially on order-book state, queue position, realized fill intensity and calibration. An OHLCV proxy would be scientifically weak.

Classification:

`avellaneda_style_mm = DEFERRED_REQUIRES_L2_QUEUE_REPLAY`

A future test is justified only with suitable L2/event-level data or prospective shadow capture.

## Final system disposition

`Hummingbot = CONCLUDED / EXECUTION_MICROSTRUCTURE_SOURCE`

Retain:
- inventory skew as a research risk overlay concept;
- Hummingbot as a source of execution/microstructure hypotheses.

Do not retain as proven alpha:
- frozen cross-exchange market-making economics tested here.

No Factory migration was performed.
