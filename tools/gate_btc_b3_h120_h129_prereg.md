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

Exact contract identity for front selection is frozen as `^(WIN|WDO)[FGHJKMNQUVXZ][0-9]{2}$`. Option tickers or any other suffix-bearing instruments are excluded before volume ranking.

When an official daily archive contains multiple BVBG.086 XML snapshots, the completed-session observation is the latest well-formed member by `ZipInfo.date_time`, with lexical filename as deterministic tie-break. A newer malformed member is rejected explicitly and recorded before falling back; missing economic fields in a well-formed latest member remain data gaps and never cause fallback. Parsing is namespace-agnostic at the `PricRpt` record boundary. Front volume uses observed `FinInstrmQty`, falling back to observed `RglrTraddCtrcts` only when the former is absent. The pinned intraday CSV bytes are decoded explicitly as Latin-1 and sealed by source-commit URL plus SHA-256 before they define the daily request set.

Historical ingestion may be partitioned mechanically across deterministic date shards. Each shard contains only official selected observations and raw/nested/XML hashes; the economic runner is unavailable until the sealed request plan is reproduced, all shard indices are present exactly once, every date is accounted for exactly once, and every chunk hash validates. Sharding changes runtime only, not source, sample, causal join, family definition, threshold, cost, or scientific gate.

The smaller BVBG.187 derivatives report is deliberately not substituted: the official B3 layout marks `TradQty`, `FinInstrmQty`, and `RglrTraddCtrcts` with rule R2, meaning those fields are not sent in BVBG.187. That surface therefore cannot preserve the observed activity semantics required here. Layout source: https://www.b3.com.br/data/files/57/85/8C/A3/5C11881036DB3088AC094EA8/BVBG.086%20para%20UP2DATA.xlsx

Per-family source coverage uses current intraday sample sessions as the denominator and requires finite exact-future fields on every raw session needed by the causal change: two completed sessions for H120-H126/H128, three for the two-shock H127 construction, and two after the frozen 60-session warmup for H129. Discovery and replication are measured separately; a family below 90% is not economically evaluated and is recorded as `DATA_GAP_COVERAGE` without affecting data-ready families.

Frozen scientific gates: >=60 trades; reference net edge >0.25 bp/trade; positive stress result; positive one-extra-bar delay; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 contribution <=40%; family breadth >=2 qualified cells plus parameter/horizon breadth; identical independent 2020_22 + 2022_24 replication rule; max 2 survivors; null valid.
