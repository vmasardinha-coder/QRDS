# F-XMM-INVENTORY — family extraction conclusion

Date: 2026-09-21

## Classification

`F-XMM-INVENTORY = HANDOFF_READY_AWAITING_ADMISSIBLE_FEATURE_HISTORY`

This is a **family-source extraction success**, not an economic alpha pass.

## Official validation evidence

- workflow: `GATE BTC F-XMM Inventory Family`
- run: `35673039175`
- preregistered head SHA: `ce313b1e1cfd9559e4096bbf7cfe3d45965699bb`
- artifact: `gate-btc-f-xmm-inventory-family`
- artifact id: `10671582660`
- artifact digest: `sha256:b9a556fed3a48b03e40bba6d1801344a7ea883b7d3df302f4ff3bb62395c809c`

## Live depth10 capability result

- accepted feature events: `1152`
- Binance: `581`
- OKX: `571`
- shared overlap: `57.92 s`
- crossed accepted books: `0`
- rejected callbacks: `0`
- callback accounting: `100%`
- quality gate: `PASS`

Selected median feature states during this one validation capture:

### Binance
- `imbalance_l1 = +0.3870`
- `imbalance_l5 = +0.3871`
- `imbalance_l10 = +0.3102`
- `imbalance_shape = +0.00066`
- `microprice_deviation_bps = +0.000224`
- `spread_bps = 0.001159`

### OKX
- `imbalance_l1 = +0.3815`
- `imbalance_l5 = -0.2349`
- `imbalance_l10 = -0.1465`
- `imbalance_shape = +0.3114`
- `microprice_deviation_bps = +0.002210`
- `spread_bps = 0.011590`

The differing venue states demonstrate that the frozen geometry captures information beyond top-of-book price alone. They do **not** establish which sign, venue, horizon or aggregation rule predicts returns.

## Tangible object delivered

Machine-readable family contract:

`artifacts/gate_btc_2/family_handoffs/F_XMM_INVENTORY_FAMILY.json`

Live deterministic extractor:

`tools/gate_btc_2_f_xmm_inventory_extractor.py`

This extracts the useful microstructure capability from Cryptofeed/Hummingbot without integrating either external system into the Factory.

## Scientific separation from rejected lead-lag

`H_CF_LL_01` remains rejected. This family does not flip the old direction, reuse its threshold or claim cross-venue prediction. It only defines contemporaneous book-state features.

## Factory handoff rule

The Factory may treat `F-XMM-INVENTORY` as a family source after an admissible timestamped/prospective feature series exists. Any direction, horizon, persistence rule, venue-combination rule, threshold or execution mapping must be created/tested as a fresh child hypothesis.

Current validation events receive zero historical PIT credit and zero economic credit.

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

`F-XMM-INVENTORY = FAMILY EXTRACTED SUCCESSFULLY / DEPTH10 GEOMETRY VALIDATED / READY FOR FACTORY HANDOFF WHEN HISTORY IS ADMISSIBLE`
