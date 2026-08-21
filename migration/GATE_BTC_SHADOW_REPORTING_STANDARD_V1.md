# GATE BTC - SHADOW REPORTING STANDARD V1

Status: FROZEN_REPORTING_CONTRACT
Mode: RESEARCH_ONLY
Operational status: NOT_APPROVED
Orders: 0
Real capital: 0

## Purpose
Freeze one deterministic daily reporting contract. Reporting must answer data trust first, then scientific/economic interpretation. A successful workflow alone is never sufficient to mark collection health green.

## Mandatory daily report set and order
1. COLLECTION_HEALTH_LANTERNS
2. EXECUTIVE_VISUAL_COCKPIT
3. MASTER_ANALYTIC
4. PROFIT_PRESERVATION

Collection Health is the trust gate for the other reports. If critical inputs are stale, missing, inconsistent, or have the wrong effective data date, derived reports must expose that state and may not present an unconditional green delivery.

## 1 - COLLECTION_HEALTH_LANTERNS
Purpose: determine whether the evidence feeding GATE BTC is trustworthy before interpreting performance.

Mandatory columns: collection/trail; lantern; effective data date/cutoff; canonical counter when applicable; freshness; concise evidence/status note.

### Group A - Execution and delivery
Local Coordinator; D50 local; Data Readiness; Daily Research main; automatic fallback; LOCK/JST input; Daily handoff; runtime pointer; dependent publishers; Reporting Current State; four-report PDF delivery.

### Group B - Measurements and economics
D50 economic/qualification; D50 Control; D50 Cost Aware; D50 Exit 2Sigma; V2A; Delta V11; Delta Paper; Delta V12; LOCK25/50; Gateway Universe/Dynamics; Bull Replay; QOS/QMASTER; MacroQuant manual feed.

### Group C - Prospective trails and auxiliary sources
CMC Top-150; B3 H1; Bybit Spot archive; Bybit Derivatives archive; Binance USD-M archive; Bybit V5 live; V2A recovery probes; RWA sidecar; V16 funding/shortability; V16B and registered challengers; PRL50; ALT Trail; QOS Three-Track; Gate BTC 2.0.

### Lantern semantics - frozen
- GREEN: current, complete and internally consistent for required cadence.
- YELLOW: usable with non-critical warning, partial redundancy, short evidence, or counter awaiting natural next observation.
- ORANGE: materially degraded or stale; interpretation must be qualified.
- RED: failed, missing critical evidence, blocked, or invalid for required cycle.
- BLUE: legitimately waiting for calendar/event/evidence; no collection failure.

### Anti-false-green rule
Workflow `success` does not imply GREEN. Validate effective evidence date/cutoff, freshness, required sections and canonical provenance. A report generated today from an older-than-required reference date is stale/degraded even if its workflow passed.

## 2 - EXECUTIVE_VISUAL_COCKPIT
Short daily decision cockpit. Mandatory: Collection Health trust headline; data as-of; changes since prior valid cycle; major engines and scientific clocks; supported regime/context; research architecture; zero-real-capital status; next material gates/dates; MacroQuant block when manual data exists, otherwise visible STALE MANUAL INPUT. Never silently omit a tracked engine.

## 3 - MASTER_ANALYTIC
Technical/auditable research book. Mandatory: provenance/cutoff; methodology/version; QA/warnings; complete engine tables; costs/drawdowns/evidence stage; canonical counters/clocks; comparison limitations; historical vs prospective distinction; MacroQuant independent manual/external trail; research verdict and next scientific decision.

### Universe A - Proxy Real Atual vs V2A aligned cycle
The Master must maintain one explicit aligned-cycle block for the current real proxy portfolio and V2A comparators.

Frozen anchor for the current real proxy: 2025-12-10, initial observed value BRL 231000. Do not inherit the synthetic proxy's 2020 history into the real proxy.

Mandatory distinction:
- `PROXY_REAL_ATUAL`: user-observed real portfolio checkpoints only.
- `VICTOR_PROXY_SINTETICO`: model/simulated V2A comparator; never relabel as real.

Mandatory comparison set when same-cutoff V2A data are available: QOS Ultra; QOS Agressiva Controlada; QOS Moderada; QOS Conservadora; Victor Proxy Sintetico; BTC; BTC/ETH 70/30.

Mandatory presentation in the Master:
1. table in BRL, all V2A series normalized to BRL 231000 at 2025-12-10;
2. line chart using the same BRL scale;
3. at minimum the checkpoints `START_2025-12-10`, `STRESS_JUN_2026`, `PRE_TURN_2026-08-14`, and `CURRENT` when supported;
4. real-proxy checkpoints must never be interpolated or backfilled; if the real checkpoint is approximate, label it approximate;
5. V2A checkpoints must come from the daily V2A series at the applicable date/cutoff;
6. report separately total-cycle performance and rebound-from-stress performance so that defense and recovery are not conflated.

Current observed real-proxy checkpoints registered for reporting context:
- 2025-12-10: BRL 231000;
- stress low around Jun-2026: approximately BRL 171000;
- 2026-08-14: BRL 179500;
- 2026-08-21: BRL 197000.

These real values are manual observed evidence, not reconstructed model data. Future updates append new observed checkpoints and do not rewrite prior checkpoints without explicit correction evidence.

## 4 - PROFIT_PRESERVATION
Dedicated preservation module. Scope: LOCK25/50 and registered preservation variants; PRL50; ALT Trail; giveback/equity preservation diagnostics. MacroQuant is outside this module except for an explicit independent-trail note when context requires it.

## MacroQuant - frozen handling
Source mode: MANUAL_FEED. Classification: EXTERNAL_NATIVE_UNCOSTED_DIAGNOSTIC. Research-only and non-blocking for automated Daily Research.

Rules: first eligible snapshot received per native date is official; later same-date snapshots diagnostic only; no reconstructed historical NAV/fills/positions; no net-after-costs winner claim versus costed engines while comparable costs are absent; include in Executive and Master when current; if no fresh manual file, keep visible as STALE MANUAL INPUT; do not treat MacroQuant as an internal Profit Preservation engine.

## PDF delivery gate - mandatory
A PDF is not GREEN/DELIVERED unless: file exists/opens; effective cutoff is correct; required sections exist; canonical counters agree with authoritative ledgers and are never inferred merely because a publisher ran; critical sections are not empty without GAP/STALE; no clipped/hidden text, overlap, broken glyphs or overflow; safety header is visible (RESEARCH_ONLY / NOT_APPROVED / orders=0 / real capital=0); report role matches this contract.

Any critical failure must surface WARNING/INCOMPLETE/FAIL rather than false green.

## Scientific safety
This contract changes reporting/provenance/freshness/visual-delivery only. It does not modify methodology, selection, weights, signals, execution, costs, promotion gates or scientific counters. No backfill or manual counter advancement is authorized.
