# Executable pending-work batch — 23 October 2026

## M3 HOLD quote dependency

Observed runtime 8c9e01aaab2838d735209bfa17c62473e7033a88 has
38 signal snapshots through 2026-10-22, but the current gross economic epoch
reports `MISSING_REQUIRED_PRICES: ZBCN` and remains at 2026-10-21/N8.
Its frozen holdings are KAIA, KMNO, NIGHT, PUMP, PYTH, RENDER, SEI, STRK,
SUI and ZRO. ZBCN is not a held asset. The next observation is HOLD/N9.

The runner incorrectly requested every current top-ten candidate on every HOLD.
It now requests held assets and BTC on HOLD, and the union of held assets,
new top ten and BTC on activation/rebalance. A missing held quote still fails;
no asset is dropped, interpolated, assigned zero or replaced by a survivor.
No ranking, weighting, rebalance clock, contract or historical ledger is changed.
An actual successful current-cutoff collection is required before marking the
delivery accepted; tests alone do not advance N.

## F-X prospective window

The first 2026-10-23 window ended at 02:45 UTC with no decision file.
The 02:00–04:00 UTC Actions collection contained 75 runs and none for this
experiment. Later status at 13:23 UTC still said awaiting first window.
This proves no published decision; it does not prove the scheduler's internal cause.

Status now reports missed dates and the next window, without late decisions,
late publication seals, outcome credit or a changed contract. The existing
workflow gains 02:05/02:20/02:35 UTC attempts and successful producer-event
fallbacks. Producer callbacks outside 02:00–02:45 UTC exit at a lightweight gate;
they do not repeatedly rebuild the historical panel. Schedules remain subject
to GitHub delivery delays; first live acceptance is still pending.

## System13 source boundary

`tools/gate_btc_system13_governed_bars.py` adds the missing strict import boundary.
It consumes a reviewed admission receipt, raw daily OHLCV evidence and observed
membership; it does not admit sources, collect data, install Qlib or train.

Required bundle schema: `qrds.system13.governed_bar_import.v1`, containing
`admission_path`, `admission_sha256`, and `bars` entries with `raw_path` and
`raw_sha256`. The admission receipt must include the exact source/instrument
bindings, USD quote currency, base-asset volume, reviewed adjustment policy,
qualification time, and hash-bound identity/tradability/adjustment evidence.
Raw daily bars use `qrds.system13.native_daily_ohlcv.v1`.

The importer rejects quotes masquerading as OHLCV, USDT relabelled USD,
USD volume relabelled native volume, changed hashes, path escapes, future
membership, unfinished or late reconstructed bars, duplicate identity/session
pairs, invalid OHLC, missing admission and non-finite values. Missing assets
remain in the coverage denominator. Fifty assets and 80% coverage are retained.

Usage for a source bundle supplied by source review:

```bash
python tools/gate_btc_system13_governed_bars.py \
  --bundle /path/to/reviewed/bundle.json \
  --membership /path/to/observed-membership.json \
  --out /path/to/new-import-review.json
```

No live source is declared qualified by this batch. No partitions are declared
qualified; `training_ready`, `holdout_read_allowed` and `system13_complete` remain
false. The frozen protocol, observed quote panel and completed System12 stay intact.

## R90 executive review — documentary conclusion

Source: acompanhamento_hipoteses(20261023-112341).md and posicoes_20261023.md,
closing 22 October BRT. R90 has 11 rejected rounds, seven open positions and
USD 2,059 cash: about 69% of the USD 3,000 base, above the fleet median of 41%.
Cash is unchanged over 14 days, so this is persistent idle capital, not a new
cash-accumulation incident. At NAV USD 3,216.44, cash is about 64.0% of NAV;
the different denominator explains the apparent 64%/69% discrepancy.

R90 gross return is +7.21%, modeled net +6.31%; R30 is +8.46%/+8.17%.
This does not isolate causation: holdings/regime and costs differ. Two September
rebalances increased R90 cash after realized profits and no clean replacement.
Continuity review recovered the completed 17 October dry-run already stored in
`artifacts/gate_btc_2/dependency_followup_20261017/`. Proposal
20261017T195537Z and validation 20261017T195859Z are hash-bound in MACRO_REVIEW.json.
The proposal retained 30-day momentum and 90-day regime, but had only four open
positions and insufficient diversification. Monte Carlo expected returns were
-0.4752%, -0.8270% and -1.1645% at 7/15/30 days; all horizons failed.
MACRO_RECEIPT.json confirms the six live portfolio hashes were unchanged.
The source scripts were run from the user's MacroQuant project, not supplied
as runnable source in this batch.

That prior review remains CLOSED_REJECTED_PROPOSAL_NO_LIVE_CHANGE. The new
22 October report has no new proposal/validation pair, so its 11-round warning
is monitoring, not grounds to reopen the completed review or claim a fresh
Monte Carlo result. A future proposal would require a separately dated review.
No new local Macro command was executed in this batch.

Existing external read-only commands, not executed in this batch:

```bash
python3 apply_rebalance.py --tag score30_regime90 --dry-run
python3 validate_rebalance.py manual_runs/portfolio_proposed_dryrun_score30_regime90.json --tag score30_regime90
```

No portfolio, source-study contract, historical outcome, order or capital state
is changed by this batch.
