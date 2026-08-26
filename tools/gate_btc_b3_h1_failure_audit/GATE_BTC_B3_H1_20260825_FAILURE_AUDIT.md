# GATE BTC B3 H1 — 2026-08-25 failure audit

The failure is classified **D — INGESTION/DISCOVERY_FAILURE**, with **G — scheduler/workflow** as a secondary operational factor. The official B3 `tickercsv` endpoint returned HTTP 200 and a syntactically valid ZIP before publication had finalized. The collector correctly preserved and hashed those official bytes, but the immutable snapshot contained only partial `WINV26` coverage and **no WDO records of any contract**. Frozen structural QA therefore correctly failed closed at `M1_WDO_MISSING`.

## Source and provenance

Failed run `32921641712` captured the 2026-08-25 source at `2026-08-26T02:09:22Z`. Artifact `9590032255` has SHA-256 `2ad0defff02f8118800ba29ec67ca32aea2e3a5a15b0c3ca274ce5059e7a62c9`. The official ZIP was 29,760,138 bytes with SHA-256 `63404a7aa5a3d6328feb9aa947b961364ed57beb597195065976f655f035e95a`; its only member was `25-08-2026_NEGOCIOSAVISTA.txt`, 300,605,216 bytes uncompressed. It represented the correct session date. No different-session confusion was found.

The raw member contained 4,229,972 rows. `WINV26` was present. No `WDO` symbol, including any alternate WDO maturity, was present. Therefore the missing WDO was in the source snapshot itself, not created by the parser.

## Frozen contracts and roll

The 25/08 contract mapping had already been frozen before the session as `WINV26 / WDOV26`, timezone `America/Sao_Paulo`, `FROZEN_BEFORE_H1`. The failed bytes contain the expected WIN and no WDO at all, so there is no evidence permitting a roll/ticker change.

The unchanged causal bindings are:

- `blind_lock_sha256=ceb5ed9b48f2c4f616eee82a78942f39deceb41272369be02ad207b49425cbf1`
- `full_frozen_schedule_sha256=5fd7314f55fb1c6394628d94227fdc0ed375016a57453a07f05828ffd5a9282f`
- `h1_schedule_prefix_sha256=c9ff28b4d1b6c8e2aceb3281da51bc41858780493c99a0eeac148f2bdd0bc4f6`
- `upstream_engine_sha256=1e313614e4f8dd318488e3abdde1d56848c076f9e57bb47a4fd5ce4f9c06410c`

All existed before the target session. No future information, retune, synthetic reconstruction or H1 economics were used.

## Raw data and deterministic M1 → M5

`WINV26` produced 431 M1 bars from `10:19` through `17:29`, with zero duplicate keys and PASS on OHLC integrity and tick grid for available rows. Deterministic M5 produced only `87/102` bars. The missing buckets are `09:00` through `10:10` inclusive in five-minute increments.

WDO produced `0` M1 and `0/102` M5 bars. The frozen lattice requires exactly 102 M5 bars per root from `09:00` through `17:25`. Both roots therefore fail the 102-bar requirement; WDO is completely absent.

## Pipeline stop

`source discovery` accepted the first HTTP-200 valid ZIP as captured before publication finalization. `download` passed. `parser` behaved fail-closed and exposed the incomplete source. `structural QA` failed at `M1_WDO_MISSING`; WIN independently had only 87/102 bars. `qualification` stayed false with no increment candidate. `append`, `gate-btc-runtime` publication and H1 reporting increment did not execute.

This is **not** case H (`VALID OBSERVATION NOT APPENDED`): the captured snapshot itself was not structurally valid. Recovery is admissible only if later official bytes for the **same already-frozen 25/08 session** pass every unchanged gate.

## Safe recovery and recurrence fix

An exact rerun of failed run `32921641712` has been requested. At audit-write time it remains `QUEUED`, so later finalized bytes have not yet been structurally proven and recovery remains fail closed at `6/20`.

The plumbing-only regression fix adds late-publication retry windows at `09:30` and `12:30 UTC` Tue-Sat. These retries still resolve only `yesterday` in UTC — the immediately preceding frozen Mon-Fri B3 session. They do not sweep older dates and do not authorize arbitrary backfill. The H1 collector, scientific schedule prefix, contracts, hashes, 102-bar gate, methodology, parameters, cutoff and economics lock remain unchanged. Regression coverage is in `tests/test_gate_btc_b3_h1_late_publication_recovery.py`.

```text
TARGET_DATE=2026-08-25
ROOT_CAUSE=Official B3 HTTP-200 ZIP was captured before publication finalized; snapshot had partial WIN and zero WDO, and plumbing had no later same-session publication-finalization retry window.
FAILURE_CLASS=D
SOURCE_VALID=false
STRUCTURAL_QA=FAIL
RECOVERY_ALLOWED=false
RECOVERY_EXECUTED=false
REGRESSION_FIX=Bounded late-publication retry windows for the immediately prior frozen session only
PRE_COUNT=6/20
POST_COUNT=6/20
LATEST_VALID_DATE=2026-08-21
H1_ECONOMICS_READ=false
ORDERS=0
REAL_CAPITAL=0
```
