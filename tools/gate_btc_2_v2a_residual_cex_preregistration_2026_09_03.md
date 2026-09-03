# GATE BTC 2.0 — residual V2A CEX preregistration batch

Date: 2026-09-03
Issue: #111
Scope: qualification-only preregistration. No source admission or historical credit.

## Frozen candidates

| Symbol | CoinGecko identity | Provider | Exact spot pair | Qualification role |
|---|---|---|---|---|
| PIEVERSE | `pieverse` | Gate Spot | `PIEVERSE_USDT` | independent physical qualification |
| REAL | `reallink` | MEXC Spot | `REALUSDT` | independent physical qualification |
| APEPE | `ape-and-pepe` | MEXC Spot | `APEPEUSDT` | independent physical qualification |
| TIBBIR | `ribbita-by-virtuals` | MEXC Spot | `TIBBIRUSDT` | independent physical qualification |
| PONS | `pons` | Gate Spot | `PONS_USDT` | independent physical qualification |

These candidates are materially distinct public source routes for names still present in the authoritative 2026-09-02 V2A failure inventory. Provider market surfaces currently expose the named pairs. Pair existence is not source admission: exact identity, raw bytes/hash, schema/time semantics, UTC cutoff behavior, continuity, duplicate/gap/OHLC/volume QA and historical admissibility remain unasserted until physical qualification.

Each candidate must fail independently. One source or symbol failure must not block or confer evidence on another candidate.

## Scientific boundary

A successfully qualified source can improve the forward collection path only unless the separate historical Dataset Seal contract independently recognizes already-existing contemporaneously admissible evidence. Newly downloaded historical candles do not retroactively become point-in-time observations and do not erase survivorship bias.

No source stitching, synthetic history, late seal, PIT repair, denominator change or post-result universe pruning.

## Safety

- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- NOT_APPROVED=true
- ENGINE_FEED=false
- ORDERS=0
- REAL_CAPITAL_BRL=0
- NO_RETUNE=true
- NO_BACKFILL=true
- NO_COUNTER_RESET=true
- NO_SILENT_SOURCE_SUBSTITUTION=true
- FAIL_CLOSED=true

System 8 / #111 remains blocked. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE`. Systems 10–14 remain dependency-bound; System 15 remains independent; System 16 remains future-controlled.
