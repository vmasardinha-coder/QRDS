# GATE BTC — Phase 2 Profit-Retention Result

Status: **RESEARCH RESULT / EXECUTION-CONSISTENT v1.1 SUPERSEDES v1 FOR DECISION**  
Pinned Phase-1 evidence: **31276127634 (#115)**  
Original exploratory Phase-2 run: **31277372106**  
Execution-consistent v1.1 run: **31277917947**  
v1.1 artifact: `gate-btc-profit-retention-execution-31277917947`  
v1.1 artifact id: `9027550308`  
v1.1 artifact SHA-256: `85e9da1a118e671f307d9d049f014627faad20f5edcddbec7479469901ccefe7`

## Why v1.1 was required

The original Phase-2 study correctly froze the entry *selection* but anchored returns at the signal-date close and allowed a lock to realize at the same close that revealed the trigger. The frozen V2A framework specifies `execution_lag_daily_bars=1`.

The v1.1 protocol was committed **before recalculating results** and keeps the economic hypothesis unchanged:

- same QOS picks;
- same +20% activation;
- same 50% giveback of peak **profit**;
- no pre-activation stop loss;
- no threshold tuning.

It changes only execution consistency:

1. entry = first validated daily close strictly after the signal date;
2. monthly baseline exit = first validated daily close strictly after the next signal date;
3. lock trigger = observed at confirmed daily close;
4. executable lock exit = first validated daily close strictly after the trigger close.

The same 62 complete >=95%-coverage signal months and 1,240 selected-alt trades remain in the paired sample.

## v1 diagnostic remains useful

The original same-close study showed a real path problem: many selected alts reached large unrealized gains and later surrendered them. That diagnosis is retained. It is **not** the operational performance estimate.

## Official execution-consistent v1.1 result

### QOS Moderada

- executable `MONTH_END`: mean selected-alt sleeve return **+0.1208%/month**;
- executable `PRL50_POSITION`: **+0.5687%/month**;
- paired delta: **+0.4479 percentage points/month**;
- paired bootstrap 95% interval: **[-1.2378, +2.0222] pp/month**;
- bootstrap probability delta > 0: **70.28%**;
- PRL50 trigger rate: **27.62%** of selected trades;
- mean executable holding: **26.36 days**; median **30 days**.

### QOS Ultra

- executable `MONTH_END`: mean selected-alt sleeve return **-0.0666%/month**;
- executable `PRL50_POSITION`: **+0.5396%/month**;
- paired delta: **+0.6062 percentage points/month**;
- paired bootstrap 95% interval: **[-0.6295, +1.7882] pp/month**;
- bootstrap probability delta > 0: **83.96%**;
- PRL50 trigger rate: **25.13%** of selected trades;
- mean executable holding: **26.73 days**; median **30 days**.

Both 95% intervals cross zero materially. The execution-consistent evidence is therefore directional but weak-to-moderate, not sufficient to establish an exit edge.

## Regime decomposition

The positive effect remains concentrated in `DEFENSIVE` periods:

- Moderada DEFENSIVE: monthly executable sleeve **-0.0377% -> +0.8240%**;
- Ultra DEFENSIVE: **-0.3278% -> +0.5012%**.

In `RISK_ON`:

- Moderada: **+0.3011% -> +0.2781%** (slightly worse);
- Ultra: **+0.2307% -> +0.5833%** (better).

This is a diagnostic decomposition only. No regime-specific rule is authorized or tuned from it.

## Name collision guard

The historical Phase-2 per-position rule is henceforth called **`PRL50_POSITION`** (Profit-Retention Lock 50).

It is **not** the pre-existing project `LOCK50`, which is a different portfolio-level hypothesis defined in `config/lock25_50_shadow_contract_v1.json`:

- portfolio equity HWM;
- arming at 1.50x cycle equity;
- 15% HWM retracement trigger;
- protection of 50% of accumulated portfolio profit into virtual cash.

The two hypotheses must never share a ledger, result series or promotion decision.

## Decision after v1.1

1. **Do not deploy the current QOS selector as-is.** Phase 1 remains negative on structural incremental selection alpha.
2. **Do not treat PRL50_POSITION as a proven repair.** Execution consistency materially weakens the historical advantage.
3. Preserve PRL50_POSITION unchanged as a **prospective shadow hypothesis only**; no additional activation/giveback tuning on this historical sample.
4. The scientifically clean prospective start is the first new monthly QOS signal after the v1.1 protocol freeze: **2026-08-31 signal**, with entry on the first eligible daily bar after it.
5. Do not initialize a prospective position mid-cycle from the July signal; doing so would inherit pre-freeze price-path information.
6. Keep the existing portfolio-level LOCK25/LOCK50 experiment independent.
7. No real capital, order generation, engine feed or operational approval follows from this result.

KAITO was not among the QOS selected trades in the >=95% complete-month historical sample and is not used as evidence.

Safety: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED`, `ENGINE_FEED=false`, entry selection unchanged, Phase-1 methodology unchanged, orders=0, capital=0.
