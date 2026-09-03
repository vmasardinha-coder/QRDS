# GATE BTC 2.0 — residual V2A CEX preregistration batch

Date: 2026-09-03
Original issue context: #111
Current role: qualification-only preregistration for the forward collection path and the authorized prospective V2A Dataset Epoch. No source admission or historical credit.

## Frozen candidates

| Symbol | CoinGecko identity | Provider | Exact spot pair | Qualification role |
|---|---|---|---|---|
| PIEVERSE | `pieverse` | Gate Spot | `PIEVERSE_USDT` | independent physical qualification |
| REAL | `reallink` | MEXC Spot | `REALUSDT` | independent physical qualification |
| APEPE | `ape-and-pepe` | MEXC Spot | `APEPEUSDT` | independent physical qualification |
| TIBBIR | `ribbita-by-virtuals` | MEXC Spot | `TIBBIRUSDT` | independent physical qualification |
| PONS | `pons` | Gate Spot | `PONS_USDT` | independent physical qualification |

These candidates are materially distinct public source routes for names present in the authoritative 2026-09-02 V2A failure inventory. Provider market surfaces exposed the named pairs at preregistration time. Pair existence is not source admission: exact identity, raw bytes/hash, schema/time semantics, UTC cutoff behavior, continuity, duplicate/gap/OHLC/volume QA and prospective exact-source qualification remain unasserted until physical qualification.

Each candidate must fail independently. One source or symbol failure must not block or confer evidence on another candidate.

## Scientific boundary

The original historical Dataset Seal is permanently `UNSEALED_FAILED` under #453 and receives no repair or credit from these sources. A successfully qualified source may improve only the forward collection path and, after separate exact-source adjudication, may become eligible for the authorized prospective epoch registry. Newly downloaded historical candles do not retroactively become PIT observations and do not erase historical survivorship bias.

The canonical prospective epoch is `GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03` from #456. D0 remains governed exclusively by the fail-closed cutover in #459: a source qualification by itself earns zero D0/epoch credit and cannot bypass the complete post-preregistration PIT snapshot, zero-failure, survivorship-free and full exact-source-registry requirements.

No source stitching, synthetic history, late seal, PIT repair, denominator change, post-result universe pruning, counter carryover or silent substitution.

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

System 8 prospective epoch remains `WAITING_D0 / COLLECT_MORE`. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE` on its independent clock. Systems 10–14 remain dependency-bound; System 15 remains independent; System 16 remains future-controlled.
