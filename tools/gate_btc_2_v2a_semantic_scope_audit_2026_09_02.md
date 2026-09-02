# GATE BTC 2.0 — V2A semantic-scope audit

Date: 2026-09-02
Authority: Dataset Seal #111 + merged satisfiability audit #416.
Scope: read-only adjudication of the current `SEMANTIC_SCOPE_REVIEW` class against rules that already existed in the frozen V2A implementation. No universe change is performed here.

## Evidence inspected

Authoritative daily runtime snapshot `2026-09-02-run-33591124479` reports attempted=150, loaded=94, failed=56. Re-running the already-canonical advisory classifier logic over the exact frozen universe/failure inputs yields:

- `SOURCE_RECOVERY_CANDIDATE`: 30
- `SEMANTIC_SCOPE_REVIEW`: 22
- `WAIT_FOR_HISTORY`: 4
- `UNMAPPED_FAILURE`: 0

The canonical classifier marks semantic cases conservatively from RWA/tokenized/cash-like name/symbol patterns, but explicitly states that the class is **review only, no automatic exclusion**.

## Frozen pre-existing universe rules

The V2A implementation already had these deterministic exclusion controls before this audit:

- `STABLES`: explicit symbol set from config plus a hard-coded stable list;
- `BLACKLIST = {LUNC, FTT, UST, USTC}`;
- `AMBIGUOUS = {LIT, XAR, VVV, STABLE, FIGR_HELOC, WBT, RAIN, CC, H, UB, BILL, LAB}`;
- `HIGH_NOISE = {FARTCOIN, TRUMP, PI}` at feature selection;
- `standard_ticker`: 2..12 uppercase alphanumeric symbols.

A case can be classified `OUT_OF_SCOPE_BY_PREEXISTING_RULE` only if one of those already-frozen controls deterministically excludes it. Semantic appearance alone is not sufficient.

## Current 22 semantic cases

| Symbol | CoinGecko identity | Semantic flag | Frozen exclusion rule matched? | Audit outcome |
|---|---|---|---|---|
| BUIDL | blackrock-usd-institutional-digital-liquidity-fund | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| USDY | ondo-us-dollar-yield | RWA + cash-like | NO | HUMAN_SEMANTIC_DECISION |
| USDGO | usdgo | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| EURSAFO | spiko-amundi-overnight-swap-fund-eur | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| EUTBL | eutbl | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| JTRSY | janus-henderson-anemoy-treasury-fund | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| USTB | superstate-short-duration-us-government-securities-fund-ustb | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| JAAA | janus-henderson-anemoy-aaa-clo-fund | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| GHO | gho | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| A7A5 | a7a5 | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| OUSG | ousg | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| KAU | kinesis-gold | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| APXUSD | apxusd | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| ONYC | onyc | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| AUSD | agora-dollar | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| CRVUSD | crvusd | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| USX | usx | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| REUSD | re-protocol-reusd | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| KAG | kinesis-silver | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| USDAI | usdai | cash-like | NO | HUMAN_SEMANTIC_DECISION |
| PC0000031 | tradable-na-rent-financing-platform-sstn | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |
| USTBL | spiko-us-t-bills-money-market-fund | RWA/tokenized | NO | HUMAN_SEMANTIC_DECISION |

## Finding

**0/22 semantic cases can be automatically removed under the pre-existing frozen V2A rules.**

The semantic classifier was intentionally advisory. None of the 22 current cases is captured by the frozen stable set, blacklist, ambiguous set, high-noise set, or ticker-format rejection. Reclassifying these names as out-of-scope now would therefore alter the universe methodology after observing the data gap.

Accordingly:

- automatic exclusion is forbidden;
- all 22 remain in-scope for the historical frozen denominator unless an explicitly authorized methodology revision creates a new prospectively frozen epoch;
- semantic cleanup cannot rescue the historical Dataset Seal under current rules;
- continuing source recovery can improve forward collection but cannot remove historical PIT/survivorship defects.

## Consequence for Dataset Seal #111

Combined with the merged satisfiability audit:

1. historical unresolved PIT defects cannot be retroactively repaired under `NO_BACKFILL=true`;
2. survivorship bias in frozen historical snapshots is not erased by newly qualified forward sources;
3. `WAIT_FOR_HISTORY` is forward-only by construction;
4. the 22 semantic cases provide **zero deterministic historical denominator reduction** under frozen rules.

Therefore there is now stronger evidence that the **original historical Dataset Seal has no demonstrated path to PASS through the current recovery loop alone**.

This audit still does not declare the original seal mathematically impossible in every conceivable legal/public-data path, because remaining `SOURCE_RECOVERY_CANDIDATE` cases may still have contemporaneously admissible historical evidence. It does establish that semantic pruning is not a legitimate shortcut.

## Next bounded checkpoint

Continue only two bounded lines:

1. exhaust materially distinct free/public/auditable sources for unresolved source-recovery names where historical admissibility could actually change readiness;
2. separately quantify the residual historical PIT/survivorship requirements that remain impossible after all admissible source evidence is considered.

If the residual set is non-zero and causally unavailable under `NO_BACKFILL`, the canonical next decision is whether to preserve the old seal as `UNSEALED/FAILED` and preregister a new forward-only dataset epoch. That epoch is **not authorized or created here**.

Safety unchanged: RESEARCH_ONLY=true, SHADOW_ONLY=true, NOT_APPROVED=true, ENGINE_FEED=false, ORDERS=0, REAL_CAPITAL_BRL=0, NO_RETUNE=true, NO_BACKFILL=true, NO_SILENT_SOURCE_SUBSTITUTION=true, FAIL_CLOSED=true.