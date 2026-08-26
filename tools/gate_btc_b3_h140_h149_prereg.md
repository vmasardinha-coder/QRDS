# B3 H140-H149 — preregistration

Parent issue: #215.

This generation is frozen before economic results and moves to official BCB/Sistema PTAX USD/BRL fixing microstructure. Source-first only: no economics until provider identity, endpoint/query, schema, timestamps, hashes, duplicate/missing bulletin checks, historical coverage and strict prior-day causality pass.

Historical cutoff exclusive `2026-08-10` America/Sao_Paulo. Same-day PTAX data may never condition a B3 session. Bulletin-dependent families become DATA_GAP if bulletin history is insufficient; daily-close data may not silently substitute for bulletin features.

Frozen families and grids are exactly those in issue #215: H140 close-return shock; H141 closing bid-ask spread shock; H142 bulletin fixing range; H143 first-to-last consultation drift; H144 late-vs-early consultation drift; H145 bulletin dispersion; H146 PTAX-vs-WDO completed-session gap; H147 two-session persistence; H148 four-vote fixing breadth; H149 lagged fixing residual. Thresholds/directions/holds remain as preregistered in #215.

Discovery `2024_26` M5; independent replication `2020_22 + 2022_24` M15. Require >=90% causal join coverage per affected family and preserve frozen costs, next-bar execution, one-extra-bar delay, side/calendar stability, concentration, >=60 trades and family breadth gates. Maximum 2 survivors; null valid.

H1 economics unread. Survivor partial prospective economics unread. No backfill, proxy substitution or retune. `orders=0`, `capital=0`, `engine_feed=false`, `NOT_APPROVED`.
