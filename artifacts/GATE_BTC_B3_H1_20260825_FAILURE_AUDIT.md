# GATE BTC B3 H1 — 2026-08-25 failure audit

## Executive finding

The 2026-08-25 H1 observation did **not** fail because of antivirus, retuning, economics, parser schema drift or a proven ticker/roll error. The official B3 `tickercsv` endpoint returned HTTP 200 and a syntactically valid ZIP while publication was still incomplete. The collector therefore captured and hashed a real official snapshot, but that snapshot contained only a late partial WINV26 session and **zero WDO rows**. The frozen structural QA correctly rejected it with `M1_WDO_MISSING`.

The exact operational weakness is source-finalization discovery: the collector treated the first HTTP-200 valid ZIP as final and the workflow had no later same-session recovery windows after the overnight publication attempts. A valid-looking but incomplete official snapshot could therefore become a permanent fail-closed observation even if B3 finalized the file later.

Primary classification: **D — INGESTION/DISCOVERY_FAILURE**. Secondary operational factor: **G — scheduler/workflow lacked late-publication retry plumbing**.

## Source / bytes

- target session: `2026-08-25`
- failed GitHub Actions run: `32921641712`
- artifact: `gate-btc-b3-h1-structural-32921641712` (`9590032255`)
- artifact digest: `2ad0defff02f8118800ba29ec67ca32aea2e3a5a15b0c3ca274ce5059e7a62c9`
- source URL: `https://arquivos.b3.com.br/rapinegocios/tickercsv/2026-08-25`
- capture window: `2026-08-26T02:09:22Z` through artifact publication at `02:09:58Z`
- HTTP status: `200`
- source state recorded by collector: `SOURCE_CAPTURED`
- official ZIP bytes: `29,760,138`
- official ZIP SHA-256: `63404a7aa5a3d6328feb9aa947b961364ed57beb597195065976f655f035e95a`
- sole ZIP member: `25-08-2026_NEGOCIOSAVISTA.txt`
- uncompressed member bytes: `300,605,216`
- parsed source rows: `4,229,972`
- WIN present: yes
- WDO present: **no WDO symbol of any contract**
- wrong-session confusion: not observed; the member/date corresponds to 25/08/2026

This is decisive against a simple parser-filter bug: the immutable raw bytes themselves contain no WDO records.

## Frozen contracts / roll

The exact 2026-08-25 mapping was frozen before the session:

- expected WIN: `WINV26`
- observed WIN: `WINV26`
- expected WDO: `WDOV26`
- observed WDO: none
- timezone: `America/Sao_Paulo`
- freeze status: `FROZEN_BEFORE_H1`

The frozen schedule already contained `2026-08-25,WINV26,WDOV26,FROZEN_BEFORE_H1` in the collector committed on 12/08/2026. Because the failed raw source contains **no WDO contract at all**, there is no evidence supporting a roll/ticker change. Changing WDOV26 would be scientifically unauthorized and is not part of recovery.

## Raw data and M1 → M5

### WINV26

- M1 bars: `431`
- first M1 timestamp: `2026-08-25T10:19:00-03:00`
- last M1 timestamp: `2026-08-25T17:29:00-03:00`
- duplicate keys: `0`
- OHLC integrity on available rows: `PASS`
- tick grid on available rows: `PASS`
- deterministic M5 bars available: `87/102`
- M5 requirement: **FAIL**
- missing M5 buckets: `09:00, 09:05, 09:10, 09:15, 09:20, 09:25, 09:30, 09:35, 09:40, 09:45, 09:50, 09:55, 10:00, 10:05, 10:10`

### WDO

- M1 bars: `0`
- deterministic M5 bars: `0/102`
- M5 requirement: **FAIL**
- all 102 expected five-minute buckets are absent

The frozen lattice requires exactly 102 five-minute bars per root from `09:00` through `17:25` America/Sao_Paulo. The failed snapshot therefore cannot qualify, even though its ZIP container and HTTP response were valid.

## Freeze / causality hashes

All four bindings carried by the failed run match the frozen H1 contract and were present before the target session:

- `blind_lock_sha256=ceb5ed9b48f2c4f616eee82a78942f39deceb41272369be02ad207b49425cbf1`
- `full_frozen_schedule_sha256=5fd7314f55fb1c6394628d94227fdc0ed375016a57453a07f05828ffd5a9282f`
- `h1_schedule_prefix_sha256=c9ff28b4d1b6c8e2aceb3281da51bc41858780493c99a0eeac148f2bdd0bc4f6`
- `upstream_engine_sha256=1e313614e4f8dd318488e3abdde1d56848c076f9e57bb47a4fd5ce4f9c06410c`

No future information, retune, synthetic reconstruction or H1 economics were used in this audit.

## Pipeline stop point

`source discovery` → **accepted an HTTP-200 valid ZIP too early**  
`download` → PASS, immutable bytes persisted and hashed  
`parser` → PASS/fail-closed, exposed partial WIN and missing WDO  
`structural QA` → **FAIL: M1_WDO_MISSING**; WIN independently also only 87/102 M5 bars  
`deterministic recomputation` → unable to satisfy complete two-root lattice  
`qualification` → `qualified=false`, `h1_increment_candidate=0`  
`append` → not run  
`publish gate-btc-runtime` → not run because structural workflow failed  
`reporting` → no H1 increment

Thus this was not case H (`VALID OBSERVATION NOT APPENDED`): the captured artifact was not a valid observation. The admissible recovery path is to re-fetch the **same previously frozen session** from the same official source after publication finalization and require every unchanged structural gate to pass.

## Safe recovery status

A rerun of the exact failed H1 job has been requested. At the time this canonical audit is written it is still `QUEUED`; therefore a later finalized official snapshot has **not yet been proven** to pass the frozen structural gates. For that reason recovery remains fail closed and the count remains `6/20`.

This is scientifically eligible for recovery only if the rerun (or an exact same-date official-source retry) proves all of the following: same frozen session and hashes, correct official provenance, WINV26 and WDOV26, exactly 102 M5 bars per root, exact M1→M5 recomputation, tick/OHLC/session/timezone gates, no synthetic fill and no economics read. Only then may the idempotent runtime publisher append the session.

## Recurrence prevention

The proposed plumbing-only fix adds two bounded late-publication retry windows at `09:30` and `12:30 UTC` Tue-Sat. They still target **only `yesterday` in UTC**, i.e. the immediately preceding frozen Mon-Fri B3 session. They do not scan older dates and do not create a general backfill permission. The collector, frozen rule, contracts, hashes, 102-bar requirement, costs, parameters and cutoff remain unchanged.

Regression test: `tests/test_gate_btc_b3_h1_late_publication_recovery.py` asserts both the bounded recovery schedule and immutability of the frozen H1 hashes, 25/08 contract mapping, 102-bar requirement and economics lock.

## Mandatory final

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
