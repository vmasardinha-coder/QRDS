# Source and training follow-up — 18 October 2026

PIT150 remains 130/150 at the 17 October close. No universe or admission was changed.

| Asset | Physical observation | Disposition |
|---|---|---|
| YLDS | 200 date labels, but daily bars are anchored at 14:30 UTC; venue metadata says FUND and proTradeAvailable=false. | UTC aggregation and market-scope review still required; no peg or direct UTC relabeling. |
| APXUSD | Kraken returned 181 closed calendar days, but only 152 of those have trades; some reported candles carry zero volume/trade count. | History/activity is insufficient. Do not promise admission after just 19 days or replace no-trade candles with invented executions. |
| OHM | 175 distinct dates in the requested 200-day window; older public request HTTP401. | Source gaps/access remain, exact-pool finding only. |
| USDAI | 183 rows but 182 distinct dates, 18 missing dates; duplicate timestamp; older public request HTTP401. | Duplicate/gap QA fails; no silent deduplication or fill. |
| USX | An exploratory pair of public pages yielded 200 closed days; the exact full collector then hit HTTP401 on its required historical page: provider message limits public access to 180 days. | Delivery not reproducibly qualified; candidate implementation was NOT activated or merged. No runtime route added. |

All requests and exact response bytes are sealed in PIT150_SOURCE_CAPTURE.zip. These findings are not global claims that an asset has no valid price on any venue. A material new source or authorized historical access can reopen the respective source investigation.

V16B.1: the publisher previously required only an externally supplied HISTORICAL_WEEKLY_UNIVERSE_MODEL_ONLY.csv. It had no route from the prospective matured corpus. The bridge verifies WEEK/MATURED, feature/exclusion/label/evidence hashes, exact prior dates, membership, finite features and causal snapshot provenance. It prepares a separate MODEL_ONLY universe only after 52 matured prior weeks; external authoritative history retains priority. Frozen feature generation, scorer, timings and chain seal gates remain unchanged. Runtime dependencies now include the source/scorer dependencies that were missing from the publisher.

Actual pinned corpus replay: 1 verified week, 111 rows, 51 weeks remaining; no derived CSV, no signal, no cycle or credit. All six source file hashes unchanged. Tests: 38 passed, 11 subtests; 51-week refusal and 52-week view compatibility with the existing frozen loader tested using synthetic fixtures, never mixed into runtime. The ordinary publisher execution must confirm the new readiness receipt after merge.
