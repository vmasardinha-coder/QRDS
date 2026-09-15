# Grammar Scout Handoff v1

Status: PREREGISTRATION-HANDOFF INFRASTRUCTURE ONLY.

This branch adds a new independent tree edge after the existing Grammar Scout. It does not modify the scout, the frozen factory grammars, H1, H31, current H counters, historical results, costs, thresholds, clocks, or prospective ledgers.

Flow:

`GRAMMAR_SCOUT_RUNTIME -> novelty signature/dedup -> ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_GATE -> existing scientific gatekeeper/factory`

Hard boundaries:
- no economics/outcome read for proposal selection;
- no allocation of an existing H ID;
- no mutation or resurrection of an existing/closed grammar;
- append-only semantic signature deduplication;
- source qualification and cost applicability remain mandatory before economic evaluation;
- no retune, backfill, counter reset, or retroactive prospective credit;
- H1/H31 remain isolated and untouched;
- this handoff cannot promote or execute a proposal; it only makes the missing autonomous queue explicit and auditable;
- every accepted proposal must pass a separate preregistration gate before any outcome read.

Safety remains RESEARCH_ONLY=true, SHADOW_ONLY=true, NOT_APPROVED=true, ENGINE_FEED=false, ORDERS=0, REAL_CAPITAL=0, NO_RETUNE=true, NO_BACKFILL=true, NO_COUNTER_RESET=true, FAIL_CLOSED=true.
