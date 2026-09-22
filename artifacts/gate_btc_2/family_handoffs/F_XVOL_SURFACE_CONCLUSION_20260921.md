# F-XVOL-SURFACE — family extraction conclusion

Date: 2026-09-21

## Classification

`F-XVOL-SURFACE = HANDOFF_READY_AWAITING_ADMISSIBLE_FEATURE_HISTORY`

This is a **family-source extraction success**, not an economic alpha pass.

## Official validation evidence

- workflow: `GATE BTC F-XVOL Surface Family`
- run: `35672747776`
- preregistered head SHA: `a05c1077a06db6b2666122a72d3771a10c512720`
- artifact: `gate-btc-f-xvol-surface-family`
- artifact id: `10671608181`
- artifact digest: `sha256:916c27fe75e3bd061a3ac905ba2e2af47d38c185775837dea33524f9210d99ab`

## Live surface capability result

The frozen extractor successfully produced a complete BTC implied-volatility surface feature snapshot from Deribit public data.

- raw instruments: `986`
- raw summaries: `986`
- accepted rows: `986`
- rejected rows: `0`
- eligible expiries: `11`
- duplicate identity failure: none
- feature snapshot: `ELIGIBLE`

Frozen emitted features for this one validation snapshot:

- `atm_iv_near = 31.91`
- `atm_iv_far = 36.77`
- `term_slope = +4.86`
- `put_25d_iv_near = 32.46`
- `call_25d_iv_near = 34.22`
- `risk_reversal_25d = +1.76`
- `butterfly_25d = +1.43`
- `surface_dispersion_near = 39.7525`

These numbers validate feature construction only. They are not trading thresholds, target values, or alpha evidence.

## Tangible object delivered

The external-system investigation now yields a machine-readable Factory-facing family contract:

`artifacts/gate_btc_2/family_handoffs/F_XVOL_SURFACE_FAMILY.json`

and a deterministic/live extractor:

`tools/gate_btc_2_f_xvol_surface_extractor.py`

This means the useful capability has been extracted from QuantLib/Deribit without integrating either platform into the Factory.

## Factory handoff rule

The Factory may treat `F-XVOL-SURFACE` as a **family source** only after it has an admissible timestamped feature history or prospective feature accumulation. Child hypotheses may vary threshold/lookback/sign only under the Factory's normal preregistration/search discipline.

The current live snapshot receives **zero historical PIT credit** and **zero economic credit**.

## Safety / evidence boundary

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`

## Final disposition

`F-XVOL-SURFACE = FAMILY EXTRACTED SUCCESSFULLY / FEATURE GEOMETRY VALIDATED / READY FOR FACTORY HANDOFF WHEN HISTORY IS ADMISSIBLE`
