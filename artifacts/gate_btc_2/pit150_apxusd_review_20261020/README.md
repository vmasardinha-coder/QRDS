APXUSD source history review, 20 October 2026

The exact Kraken APXUSD/USD source was rechecked through the completed UTC day 19 October. There are 183 unique daily rows, from 20 April through 19 October, with no missing days or duplicates. Seventeen more daily observations are required to reach the existing minimum of 200; the earliest date is 5 November if the series continues daily.

This is a source history count, not PIT150 admission. Instrument identity, OHLC invariants and raw payload hashes are recorded in REVIEW.json. Raw API responses are preserved unchanged inside RAW_SOURCE.zip; ROWS.json holds the normalized observations. The existing review ledger dated 15 October is historical and remains unchanged. No price filling, proxy, scope change or scientific credit was applied.

Reproduce using gate_btc_2_v2a_source_batch_20260905_qualification.qualify_kraken with the existing APXUSD target, START=2026-01-01 and END=2026-10-19. This uses native daily OHLC rows and excludes the current incomplete candle.
