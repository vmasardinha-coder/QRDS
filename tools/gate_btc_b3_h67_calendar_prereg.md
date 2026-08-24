# B3 H67 official-calendar binding

Status: RESEARCH ONLY — PRE-RESULT
Parent generation: #124
Operational issue: #151

## Safety and isolation
Historical cutoff is exclusive `2026-08-10` America/Sao_Paulo. H1 economics and every partial prospective survivor economics stream are forbidden inputs. Orders=0, real capital=0, engine_feed=false. No synthetic backfill, no post-event surprise values, no retune after results.

## Official observed inputs
Only scheduled-event calendars are observed inputs. Priority sources are Federal Reserve Board FOMC official current/historical calendar pages and Banco Central do Brasil official Copom calendar/publication pages. Each fetched source must record URL, provider, SHA-256 of raw bytes, parser version, fetch status and covered years. Event dates are data; weekday and month-turn flags are deterministic causal derivatives from B3 session dates.

If official scheduled-event coverage cannot be established reproducibly for the required discovery/replication dates, the affected event flag is `DATA_GAP`; it must not be silently reconstructed from statements, market moves, news or synthetic dates.

## Frozen H67 cell budget before economics
Flags:
- `FOMC_DECISION_DAY`: scheduled final day of a regular FOMC meeting only; unscheduled emergency/notation votes excluded.
- `COPOM_DECISION_DAY`: scheduled final day of a regular Copom meeting only.
- `MONTH_TURN`: first or last B3 session of each calendar month.
- `WEEKDAY_EDGE`: Monday or Friday B3 sessions.

Signal state: sign of the traded leg's own first-30-minute B3 move, observed before decision.
Mappings: `CONTINUE` and `FADE`.
Traded legs: `WIN`, `WDO` separately.
Holding horizons: `60m`, `120m`.
No threshold search is allowed for H67.

## Frozen execution and gates
Use the same H30-H69 costs by traded leg, next-bar-open execution after the first 30m observation, one-extra-bar delayed-entry stress, minimum 60 trades, positive reference edge >0.25 bp/trade, positive stress-cost and delayed-entry edge, both sides >=15 and positive, >=2 eligible half-year buckets with >=15 and positive, and top-5 positive contribution <=40%. Family discovery breadth requires >=2 qualified cells and mapping/horizon breadth on at least one traded leg. Independent replication must satisfy the same family rule on the frozen older block. Null result is valid.
