# Freqtrade standalone benchmark POC

Purpose: evaluate Freqtrade as an independent external benchmark before any QRDS integration.

This POC is deliberately isolated from the QRDS runtime. It does not use exchange credentials, does not place orders, and does not touch real capital.

## Concrete outputs

The workflow runs a reproducible BTC/USD 1h reference strategy and produces:

- Freqtrade backtest report and exported trades
- console summary with return, trade count and drawdown
- `lookahead-analysis` report
- `recursive-analysis` report
- exact strategy/config used in the run

## Why a deliberately simple strategy?

The first stage evaluates the engine, diagnostics and artifact quality, not alpha. A simple EMA crossover makes it easy to inspect whether the engine behaves as documented. The second stage ports one QRDS strategy unchanged and compares the two engines under matched assumptions.

## Acceptance gate for stage 1

1. Backtest completes on BTC/USD 1h public data.
2. Result artifact is exported and reproducible.
3. `lookahead-analysis` reports no unexplained lookahead bias.
4. `recursive-analysis` reports no unexplained indicator instability at the selected startup window.
5. No API key, authenticated exchange session, order placement or real capital is used.

## Stage 2: QRDS parity test

Only after stage 1 passes:

- choose one existing QRDS strategy/model replay;
- freeze the same OHLCV dataset and timerange;
- normalize initial capital, fee, sizing, timeframe and entry/exit semantics;
- implement the same decision rule in Freqtrade without retuning;
- compare signal timestamps, trade list, equity curve, terminal return and max drawdown;
- classify every divergence as data alignment, signal semantics, fill model, fees, compounding, candle/intrabar assumptions, or an implementation defect.

Freqtrade remains an external audit engine unless the parity experiment shows a measurable reason to integrate more deeply.
