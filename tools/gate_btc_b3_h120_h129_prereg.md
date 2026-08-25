# B3 H120-H129 preregistration

Parent issue: #205. Status: RESEARCH ONLY — PRE-RESULT.

Historical cutoff exclusive 2026-08-10 America/Sao_Paulo. H1 economics and all partial survivor prospective economics are forbidden inputs. orders=0, capital=0, engine_feed=false, NOT_APPROVED.

Frozen family budget before results:
- H120 trade-count intensity change z 1.0/1.5, same/opposite mappings, 60/120m.
- H121 average trade size = observed volume / observed trade count; change z 1.0/1.5, continuation/fade and cross inverse, 60/120m.
- H122 turnover = observed volume / observed OI; change z 1.0/1.5, same/opposite, 60/120m.
- H123 range-per-trade = observed high-low / observed trade count; change z 1.0/1.5, stress/inverse, 60/120m.
- H124 WIN-WDO relative standardized trade-count change, abs 1.0/1.5, continuation/reversal, 60/120m.
- H125 WIN-WDO relative average-trade-size shock, abs 1.0/1.5, same/inverse, 60/120m.
- H126 prior price-sign x trade-count-change-sign four-state confirmation/disagreement, fixed continuation/fade, 60/120m.
- H127 two-session trade-count persistence, second magnitude >=0.75/1.0, continuation/fade, 60/120m.
- H128 breadth vote WIN/WDO trade count + WIN/WDO average size, require 3/4 or 4/4, vote/inverse, 60/120m.
- H129 rolling-60 causal residual of prior WIN return on lagged WIN/WDO trade-count changes + relative average size; residual abs z 1.5/2.0; current WIN first-30m continuation/mean-reversion, 60/120m.

Source QA before economics: official B3 PriceReport/derivatives-report bytes only. Record URL, raw/nested hashes, schema, date semantics, contract identity/front selection, dedupe, coverage and causal availability. Observed fields and derived fields remain explicit. No synthetic trade count, OI, volume, high/low or historical reconstruction. Every family requires >=90% eligible-session join coverage in discovery and replication; otherwise only that family is DATA_GAP.

Frozen scientific gates: >=60 trades; reference net edge >0.25 bp/trade; positive stress result; positive one-extra-bar delay; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 contribution <=40%; family breadth >=2 qualified cells plus parameter/horizon breadth; identical independent 2020_22 + 2022_24 replication rule; max 2 survivors; null valid.
