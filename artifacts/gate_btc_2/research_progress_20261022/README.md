# Bounded progress: F-XAGENT child and System13 panel — 22 October 2026

## What changes

The original disagreement family stays a feature-only, unapproved handoff.
A separate child experiment now has a frozen exposure, timing, cost and
outcome protocol. System13 gains an index/materializer for the exact universe
and quote observations already archived by V2A, plus a frozen future research
protocol. Neither is an economic approval or permission to trade.

### F-XAGENT-DISAGREE-SPOT-CONTINUOUS-V1

One hypothesis only: does continuously reducing positive-consensus exposure
by observed disagreement improve paired net returns versus unscaled consensus?

- Baseline weight = max(0, mean of the three component signals).
- Candidate weight = baseline * (1 - pairwise disagreement).
- Instrument = BTCUSDT spot; remaining allocation is unremunerated cash.
- No short, leverage, threshold grid, model search or historical economic credit.
- Freshness <=90 minutes, all three independent evidence classes required.
- Missing/stale/future/unavailable inputs abstain explicitly, without zero fill.
- First decision date UTC: 23 October; decision window 02:00–02:45; entry 03:00;
  exit at the same minute 24 hours later. All times are UTC.
- Decision bytes must be published in a Git commit before entry. A second
  publication binds the decision hash to that commit. Without proof, no outcome
  gets credit. Git objects are retrieved and checked when needed.
- Outcome uses exactly the declared closed 1-minute candles, not nearby prices.
- Costs 10 bps/side and stress 20 bps/side. Unit capital reserves the entry fee;
  sell cost is charged at liquidation. BTC paired baseline pays the same roundtrip
  convention; it is not mislabeled as frictionless buy-and-hold.
- 60 paired outcomes before review; no automatic promotion or capital action.
- Results are paired event diagnostics, not a compounded deployable basket NAV.

These are preregistered research choices, not evidence that the mapping is
profitable. The original producer semantics are preserved; their economic
predictiveness is precisely what this new experiment has not yet established.

### System13 observed panel

V2A has 75 append-ledger snapshots plus two legacy registry-PIT files. The
existing validator excludes the latter under their separate schema. Every
indexed snapshot validates record and archive hashes before materialization.

The universe archive contains current_price and last_updated. Example source:
market data_as_of 21 October, capture 22 October 05:24 UTC, BTC quote 22 October
04:41 UTC. It is invalid to call this an official 21 October daily close.

The derived panel therefore retains every observed coin ID and its flags,
marks missing/stale/future quotes explicitly, and uses source_run_utc as the
observation axis. Equal ticker strings never merge different identities.
Historic prospective observations are indexed, without reconstructing missing
universes, prices or scientific credit. No current-survivor substitution.

The archives do not provide governed open/high/low/close/volume/factor bars.
Alpha158 input geometry, source/tradability/corporate-action qualification and
chronological sample requirements remain blockers. System13 is not complete.

A separate protocol freezes model class/parameters, baseline, costs and a
60 warmup / 120 train / 5 purge / 30 validation / 5 embargo / 60 holdout sequence of eligible
sessions. No automatic model training, holdout read or import of the external
CSI300 economics is enabled. A calendar/history gate alone cannot waive the
missing data semantics.

## Publication and acceptance

The workflow validates on PR, collects on push/schedule/manual dispatch,
and can stage only two new runtime namespaces. Parent handoffs, canonical 580,
H1/H31, System12 and all capital lanes are outside the publication scope.

Acceptance needs a real panel build on the archived corpus and the first
natural future XAGENT decision/seal. First P&L requires the 24h horizon and the
next collection after maturity. Before then, economic N is honestly zero.
