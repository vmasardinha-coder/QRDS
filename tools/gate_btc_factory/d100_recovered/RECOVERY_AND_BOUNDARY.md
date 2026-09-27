# D100 recovery and implementation boundary — 2026-09-27

The original local D100 contract was recovered from the installed D50 project.
It is retained byte-for-byte, including its BOM. Its SHA256 matches the existing
local PREREG_SHA256.txt: `316600073946CCB217ED81797C23C3253F034509F94F926EFB6198343AF88052`.
Matching local files establish consistency, not an independent historical timestamp.
The FROZEN_DORMANT field is historical and does not revoke the later activation.

Activation authority already exists in QRDS issue #358. D50 30/30 was reached
on 2026-08-31 and activation approved on 2026-09-01. D50 N80 is NOT a D100 start
requirement. The 2026-09-05 cloud activation was a data-feed authorization and
has produced heartbeat only. No prior heartbeat is converted into a data sample.

Recovered reference hashes (copies only; live D50 files remain untouched):

| File | SHA256 |
|---|---|
| d100_prereg_contract_v1.json | 316600073946CCB217ED81797C23C3253F034509F94F926EFB6198343AF88052 |
| d50_candidates_prereg_v2.json | 3DD1CA2B7C78C1006DB18F1738E8413BB4E2FDBBF2214CD721E3F6A4395C3EBE |
| config_delta_v11.json | EFB336B0EEBB5886B28C1FE47B8F266464D65F5FDDD551F2CAED659B6A094A6A |
| ingestion_source_map_v2.json | BA382E720C57B13F03A86838D25BA451492050D043F45010640D3D1ACC5BF487 |

## Physical data repair

The D100 workflow now physically captures the current CMC ranked Top100, with
the exact identity/rank response, actual availability timestamp and source bytes.
The CMC endpoint is already used by QRDS contemporaneous universe collection.
For diagnostic market-data coverage, it captures official OKX live linear USDT
swap metadata and latest closed daily candles/settled funding for unambiguous
exact symbol candidates. OKX daily swap/funding is the recovered D50 source
family. No alternative exchange or ticker alias is substituted.

Exact ticker matching is NOT asserted to prove asset identity. The stored data
are evidence for source qualification, not admitted execution inputs. Neither
current membership nor a newly downloaded prior close is assigned a historical
signal date. All scientific/economic credit remains zero. No P&L is computed.

Each capture has immutable gzip raw-source archives and a hash-chained manifest.
Counters distinguish physical attempts, distinct UTC days, successful days and
scientific observations. Same-day success is idempotent; failures retry without
deleting the prior attempt. Corrupt or missing archives fail closed.

Failed downloads/schema/coverage return nonzero, publish their failure status
when safe, and make the workflow fail after preserving diagnostics. No heartbeat
freshness check suppresses real collection or authorizes a scientific counter.

## Remaining scientific boundary

The recovery changes the old diagnosis “spec not recovered” to “spec recovered,
but incomplete for scored activation”. Historical September governance records
are retained; this note documents their later evidence, not a rewrite of history.

1. D100 final N and D50-vs-D100 comparison are not defined. D50 has an N80 primary
   checkpoint while its underlying Delta configuration has an N60 evidence gate;
   neither can silently become D100's final gate.
2. D100 requires liquidity and exclusions but gives no numeric liquidity rule or
   authoritative exclusion/identity registry for the expanding universe.
3. D50's source map binds 20 assets, not all assets in the current Top100. Raw
   source discovery does not automatically qualify 100 execution identities.
4. The dynamic universe needs an explicit policy for held assets leaving the
   universe and for missing price/funding data, alongside position limits.

No new threshold, scored anchor, final checkpoint or economic selection is
activated by this repair. `PROTOCOL_COMPLETION_PROPOSAL.md` is a concrete draft
for the missing decisions and has NO runtime authority. It is not read by code.
