# QRDS / GATE BTC — Project Context README

> Canonical orientation document for resuming work without restarting investigation.
> Snapshot date: 2026-09-10.
> Dynamic counters/statuses MUST be refreshed from runtime before action.

## 1. Purpose

QRDS combines:
1. cyclical allocation and long-horizon capital planning;
2. short-horizon long/short alpha research;
3. regime / momentum / structural diagnostics;
4. profit-preservation overlays;
5. external benchmarks and independent agents;
6. scientific validation, prospective collection and fail-closed governance.

High-level flow:
CYCLE / ALLOCATION → REGIME / CONTEXT → SHORT-HORIZON ALPHA → PROFIT PRESERVATION → BENCHMARK / INDEPENDENT COMPARISON → PROSPECTIVE SCIENTIFIC VALIDATION → HUMAN REVIEW

## 2. Permanent safety boundary

Preserve exactly:
- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- NOT_APPROVED=true
- ENGINE_FEED=false
- ORDERS=0
- REAL_CAPITAL=0
- NO_BACKFILL=true
- NO_LATE_SEAL=true
- NO_COUNTER_RESET=true
- NO_RETUNE=true
- FAIL_CLOSED=true
- H1_ECONOMICS_READ=false

Never alter methodology, thresholds, windows, counters, source semantics, scientific clocks or safety flags merely to unblock a track.

## 3. Functional architecture

### A. Cycle / Allocation
Answers where capital should sit across the cycle and how that affects the long-horizon goal.

Main systems:
- QOS Ultra
- QOS Moderada
- QOS Conservadora
- QOS Agressiva / Agressiva Controlada
- Victor proxy
- BTC / BTC-ETH benchmark lines
- Portal BTC cyclical selectors
- Meta 2030
- Monte Carlo / target probability / risk-of-ruin / drawdown scenarios

### B. Short-horizon Alpha / Trading Research
Answers whether a systematic strategy can generate alpha independent of market direction.

Main systems:
- Delta internal V11
- Delta internal V12
- Delta Cloud / Anthropic V11
- Delta Cloud / Anthropic V12
- External commercial Delta benchmark
- Macro Quant
- D50 family
- D100
- B3 H1 / H31 / family survivors
- Strategy Factory / autonomous family generation
- Portal BTC Momentum / Reversal / sector mechanisms

### C. Regime / Structural Context
Answers whether market behavior, momentum or structure is changing.

Main systems:
- Momentum M1 / M2 / M3
- Gateway Dynamics
- Bull Replay
- B3 H1 / H31 structural observations
- Portal BTC regime / momentum / reversal components

### D. Profit Preservation
Answers how much of a profitable path can be retained without destroying edge.

Main systems:
- LOCK25
- LOCK50
- PRL50
- ALT Trail
- Delta StopVol variants
- D50 Exit 2Sigma
- D50 Cost Aware variants
- Macro Quant internal preservation experiments

### E. Benchmarks / Independent Controls
Answers whether internal results are genuinely competitive.

Main comparators:
- BTC puro
- BTC/ETH
- QOS controls
- External commercial Delta
- Macro Quant
- Portal BTC
- Atlas / Manual
- Autonomous Portfolio
- Agent Trader / independent cloud agents
- external index / strategy benchmarks

## 4. Critical distinction: Delta vs D50

These are separate families.

### Delta internal QRDS
- V11 70/30
- V11 70/30 StopVol
- V11 50/50
- V11 50/50 StopVol
- Delta Paper collector
- Delta Formal / canonical line
- V12 independent engine

V12 is independent from V11 and must preserve its own anchor, counter, report, ledger, workflow and append-only progression.

### Delta Cloud / Anthropic
Externally produced cloud research tracked separately from QRDS internal Delta:
- Cloud / Anthropic V11
- Cloud / Anthropic V12

Do not silently merge their counters, economics or methodology into internal QRDS V11/V12.

### External commercial Delta
User-supplied screenshots/checkpoints of a commercial long/short Delta strategy.

Role:
- external benchmark only;
- no tuning source;
- freeze on last observed checkpoint if no new user update;
- never interpolate missing points.

### D50 family
D50 is NOT a Delta sub-strategy.

Main arms:
- D50 Control
- D50 Cost Aware
- D50 Exit 2Sigma
- D50 Cost Aware Vol20
- D50 readiness
- D50 data qualification
- D50 position audit
- D50 historical diagnostic replay

## 5. Canonical runtime / internal map

### Factory
- Factory Supervisor
- Grammar Scout
- Strict V2 Source Search
- Invalidated Requalification
- Autonomous Science generations
- generation ledger
- survivors / rejected/null families
- prospective survivor ledgers

### B3 / structural
- b3_h1
- b3_h1_inspired_challengers
- b3_h31_prospective
- b3_h31_shadow_paper
- b3_win_wdo_univariate
- D100

### Crypto / prospective
- gateway_dynamics
- delta_paper_monitor
- delta_v12_engine
- delta_v12_prices
- momentum_m1_m2
- momentum_m3 when eligible
- d50
- lock25_50
- prl50_position
- alt_trail40_10
- bull_replay_live_shadow
- qos_three_track

### V16
- v16_family
- v16b terminal parent
- v16b1 successor
- v16c
- v16d
- v16e

### Gate BTC 2.0
Canonical roadmap remains 16 systems:
- Systems 1–8: mature foundation
- System 8: prospective dataset epoch / 137-source registry
- System 9: forward microstructure evidence collection
- System 10: structurally ready, waiting Stage 9 exit
- Systems 11–14: downstream research chain
- System 15: LEAN-B3 + Strategy Factory active in parallel
- System 16: future controlled

## 6. Local machine layer

Known local layer:
- MT5 / BTG read-only
- Local Shadow Supervisor
- H31 intraday shadow
- H31 event spool
- H1 Inspired Challenger shadow
  - H1C_REVERSION_60
  - H1C_TREND_60
- local scheduled tasks / clocks
- local spool/autopsy/status outputs

A local status file is usually an observation/view of an existing track, not an additional independent strategy.

Typical local B3 sequence:
- ~09:00–09:15 initialization / warmup / source binding
- ~09:30 H31 decision window
- ~10:00 H1 decision
- 10:05 H1 entry when triggered
- 11:05 H1 close
- ~11:10 status / summary / autopsy

## 7. External / user-supplied layer

### Portal BTC
Track separately:
- A Ingênuo Top100 / Top300
- B Critérios Top100 / Top300
- C Vol-Weighted Top100 / Top300
- D RSI Guard Top100 / Top300
- G Rotação/Setorial Top100 / Top300
- H Benchmark Externo Top100 / Top300 when available
- Momentum leg
- Reversal leg
- sector views
- Institutional Thesis Watchlist
- price sanity quarantine
- rejected assets
- daily ledgers
- backtests
- current holdings
- closed trades
- extreme trades

### Macro Quant
Separate external short-horizon long/short research/trading project with its own selection, stop/volatility logic, preservation overlays and portfolio-generation logic.

### Atlas / Manual
- Produção
- Dinâmica
- Ref50
- Score30/Regime30
- Score45/Regime45
- Score30/Regime90
- real manual view
- normalized view
- outlier/luck diagnostics

### Autonomous Portfolio
- Crypto
- USA
- B3
- Structured B3
- benchmarks
- alpha
- positions
- changes
- attribution

### Meta 2030
Goal & Capital Allocation layer:
- starting-capital scenarios
- target capital
- Monte Carlo when scientifically supportable
- target probabilities
- risk of ruin
- drawdowns
- allocation scenarios
- BTC Deployment Protocol
- Random Selector Control where applicable

### Agent Trader / Cloud agents
Independent autonomous experiment layer used to test whether autonomous agents can beat defined benchmarks. No automatic canonical authority.

### User uploads
Uploads are evidence containers, not automatically separate systems:
- D50 dumps/status
- H1/H31 status/events/autopsies
- Portal BTC backups
- Macro Quant status
- Delta Cloud/Anthropic V11/V12 reports
- external commercial Delta screenshots
- Agent Trader outputs
- Atlas/manual reports
- supervisor logs

Map every upload to its originating track before counting it.

## 8. Current operational state — snapshot 2026-09-10

Refresh runtime before using counters.

### GREEN / collecting
- Factory Supervisor
- Grammar Scout
- Gateway Dynamics
- Delta Paper
- Delta V12
- Momentum M1/M2
- D100 forward collection
- Gate BTC 2.0 V2A Registry PIT 137/137
- Gate BTC 2.0 Dataset Epoch
- Stage 9 forward collector
- H1 local shadow
- H31 local shadow
- GitHub/runtime publishers generally operational

### YELLOW / waiting clock, sample or publication
- Momentum M3
- D50
- LOCK25/50
- PRL50
- ALT Trail
- Bull Replay
- QOS Three Track
- B3 H1 canonical
- B3 H31 canonical
- V16B.1
- V16C / V16D / V16E
- Gate BTC 2.0 System 10+
- external systems when latest user update is stale

### RED / parked fail-closed
- Strict V2 invalidated-family source gate
- 512 waiting invalidated families
- H2730-H2739 official tick source dependency

### TERMINAL / CLOSED
- original V16B
- Selector Alpha frozen/refuted program

## 9. Strict V2 parked blocker

Frozen contract:
- WIN B3 mini index futures
- M5
- strict window 2025-01-01 through 2026-08-09
- 322 eligible sessions minimum
- known strict builder result: 248 eligible
- deficit: 74
- no V1 credit
- no backfill
- no reconstruction
- no threshold reduction
- no counter reset
- fail closed

Operational policy:
- automated source search may continue;
- manual repeated source hunting is parked;
- reopen only on materially new admissible source evidence.

## 10. Stage 9 / Gate BTC 2.0

Frozen exit segment:
- activation >= 2026-09-08T00:00:00Z
- required N = 168
- all 24 UTC hour bins
- all 7 UTC weekdays
- >=167 elapsed hours
- earliest decision = 2026-09-14T23:00:00Z
- preactivation observations receive zero exit-gate credit

## 11. Economic-view classification

### Economics/history available or partially available
- historical QOS / cyclical portfolios
- Meta 2030 Monte Carlo scenarios
- historical Delta V11 comparisons
- user-supplied Delta Cloud/Anthropic economics when provided
- external commercial Delta checkpoints
- Macro Quant reports
- Portal BTC backtests / holdings / trades
- Bull Replay descriptive financial comparison
- preservation studies with explicit observed results
- D50 diagnostic/historical economic evidence where explicitly sealed

### Economics locked / not yet legitimately available
- strict V2 waiting families
- H2730+ source-blocked generations
- Momentum M3 before eligible prospective evidence
- V16B.1 / V16C / V16D / V16E before valid cycles
- H31 canonical where economics remain locked
- source-gated tracks whose contract forbids economics pre-read

Never infer economics from inventory-only or shadow-only evidence.

## 12. Resume protocol for future chats

1. Read this document first.
2. Fetch current gate-btc-runtime branch head.
3. Fetch current canonical runtime status files.
4. Runtime wins for counters/freshness.
5. Do not restart exhausted investigations.
6. Never confuse internal Delta, Cloud/Anthropic Delta, external commercial Delta and D50.
7. Map user uploads to their originating track before counting.
8. Treat reporting/inventory as reporting, not scientific authority.
9. Never read locked economics.
10. If user says only "continue", execute the next legitimate action.
11. If no material action is due, report WAIT / CLOCK / PARKED instead of fabricating activity.

## 13. What each block answers

| Block | Primary question |
|---|---|
| QOS / Meta 2030 / cyclical Portal | Where should capital be positioned across the cycle? |
| Delta / Macro Quant / H families / D50 | Can short-horizon systematic alpha be generated? |
| Momentum / Gateway / H1-H31 | Is market regime/structure changing? |
| LOCK / PRL / ALT / StopVol / 2Sigma | Can profit be retained without destroying edge? |
| External Delta / Agent Trader / Atlas | Are internal systems genuinely competitive? |
| Factory | Can new hypotheses/families be generated and falsified safely? |
| Gate BTC 2.0 | Is the data/evidence/execution-research infrastructure scientifically trustworthy? |
| Meta 2030 | Does the combined research improve the path toward the long-term capital objective? |

## 14. Core principle

NEW IDEA → FREEZE → SOURCE QA → VALIDATION → INDEPENDENT EVIDENCE → SURVIVAL → PROSPECTIVE CLOCK → ECONOMICS WHEN AUTHORIZED → HUMAN DECISION

Negative evidence is preserved. Failed hypotheses are not retuned into survivors.
