# GATE BTC Factory — Canonical History Reconciliation — 2026-09-07

Purpose: prevent stale aggregate status files from overriding newer canonical repository history, track-specific runtime evidence, workflow results, merged fixes, or explicit frozen-clock rules.

## Authority precedence

When reconstructing current Factory/collector state, use this order:

1. Latest merged PRs/commits that materially change the specific track.
2. Latest successful workflow/runs for that track.
3. Latest track-specific `gate-btc-runtime` status/ledger/receipt.
4. Latest machine-readable reconciliation or current-state export that explicitly references those authorities.
5. Aggregate health/reporting files only when they are contemporaneous and consistent with items 1–4.

A stale aggregate must never resurrect a blocker that later commits/workflows resolved. A track-specific frozen calendar/archival state must not be reported as a broken daily collector solely because its status file is older than a generic freshness threshold.

Permanent safety boundary remains unchanged: research-only, shadow-only, not approved, no engine feed, zero orders, zero real capital, no backfill, no late seal, no counter reset, no retune.

## Reconciled tracks

### D50

Old aggregate symptom: `RED_STALE` and legacy runtime mirror showing data through 2026-08-22.

Historical corrections that supersede treating that legacy mirror as the current operational authority include:
- `534da4271e1751ca71a94978c2d4d7f26c757da5` — Factory: make D50 watchdog runtime-authoritative.
- `31d56a1afb7e024f5d56eaa4c318cd5d93e2aeff` — CI: stop pinning live V2A and D50 historical state.
- Earlier recovery/reconciliation chain includes `74c35f614c34d3c167478bc233b7c2daf632d72a`, `cfdbb9c66994764f8df616496d1c7ecb73290b7f`, and `b8370e4ea90743e8df234cd1249716d3eb1a59d0`.

Reconciled interpretation: do not classify D50 as an unresolved collector outage from the legacy 2026-08-22 mirror alone. Current health must be determined from the runtime-authoritative watchdog and current forward-only producer. No missed causal window may be reconstructed or credited.

### V16B

Old aggregate symptom: stale `SCIENTIFIC_BLOCK` based on missing causal feature-panel producer/mapping.

Subsequent canonical work materially changed that state:
- `ca605c334e12cd1934e617f18fd140f64965baf5` — derive future canonical windows from frozen weekly anchor.
- `69790752f4e25bf2bfdafa67b845b7d68689d0fe` — roll watchdog on frozen weekly clock without late rescue.
- `2b7222b790fdcfb1c1e29c0f2c2d47c6f8a68fa0` — wire V16B into bounded operational auto-repair.
- `ce3b4b47fa73bbd559a4c85525d612b91f3658d4` — make causal preflight stage-aware and keep executability fail-closed.
- `b56456efb440e7292928069383ff3a9cea4fc40e` — stage-aware causal executability preflight.
- `2d619ddee21b6ec542d4bc81e29d38f272875c01` — retained full-chain rehearsal test.

Current canonical window carried by the project is signal 2026-09-10, entry 2026-09-11, complete exit 2026-09-18, canonical cycle count 0, with rehearsal/preflight required before the canonical event. Old 2026-08-27/28 missed-window status is historical evidence only and must not be surfaced as the current blocker.

### ALT_TRAIL40_10

Old aggregate symptom: `RED_STALE` because the archive/status was older than generic freshness expectations.

Canonical history:
- ALT is a frozen calendar-gated/prospective archive, not a generic daily collector.
- `47da426b531858648479f240694f5d26546df3bc` explicitly restored Factory collection health and allows ALT to resume prospectively after recorded gaps.

Reconciled interpretation: ALT gaps remain recorded and are never backfilled, but stale archive age alone is not an operational failure. Health must be evaluated against its own expected-run/calendar contract.

### PRL50

Old aggregate symptom: `RED_STALE` while source status was `ACTIVE_PROSPECTIVE_ARCHIVE`.

Canonical history:
- `47da426b531858648479f240694f5d26546df3bc` preserved the monthly signal, added executable-price collection, recovered the active month-end signal from immutable history, and added the hold-vs-preservation economic mirror.
- Earlier contract/runtime alignment includes `122d9b4a8c8b10eb4f53550a77a0389b62b2ba7b`, `d72c459e6b7ccdd643df4e5f846145c316840d17`, and the original prospective archive chain.

Reconciled interpretation: PRL50 is monthly/calendar driven. Do not mark it as a broken daily collector solely because a generic freshness clock sees an old archive timestamp. Use its expected month-end signal/price-collection cadence.

## Reporting correction

`runtime/GATE_BTC_HEALTH_DIMENSIONS.json` generated on 2026-09-07 must be treated as an aggregate diagnostic snapshot, not a higher authority than the track history above. Its red labels for D50, V16B, ALT_TRAIL and PRL50 are not sufficient by themselves to declare those four current unresolved collection failures.

Future reports must distinguish at minimum:
- `BROKEN_EXPECTED_RUN`
- `CURRENT_ACTIVE`
- `CALENDAR_GATED_CURRENT`
- `ARCHIVE_CURRENT_FOR_CONTRACT`
- `SCIENTIFIC_BLOCK_CURRENT`
- `HISTORICAL_BLOCK_SUPERSEDED`
- `STALE_AGGREGATE_DO_NOT_USE`

## Current collection focus

Do not reopen already-resolved blockers. The shared Factory/Collector Supervisor should instead:
- verify each track against its own expected-run schedule;
- alert only on genuinely missed expected runs;
- preserve causal gaps without reconstruction;
- use current runtime-authoritative producer/watchdog state;
- keep frozen tracks frozen;
- avoid deriving scientific/economic conclusions from partial prospective data.

This reconciliation is governance/history only. It changes no scientific method, threshold, clock, evidence credit, economics, orders, capital, engine feed, or promotion authority.
