# Vendor/source qualification request — WIN B3 M5 Strict V2

We need to qualify a historical data source for a research-only, fail-closed study of B3 Mini Ibovespa Futures (WIN).

Required coverage:
- Exact instrument: WIN individual B3 Mini Ibovespa Futures contracts, with auditable contract identity/expiry mapping (not only a silently stitched continuous series).
- Window: 2025-01-01 through 2026-08-09.
- Granularity: native 5-minute OHLCV, OR tick-by-tick/trade-by-trade data that can be deterministically aggregated to 5-minute bars.
- Coverage floor: at least 322 valid trading sessions, including at least 161 sessions in 2025 and at least 161 sessions in 2026 through 2026-08-09.

Please confirm, preferably in writing/documentation:
1. Whether the requested period is available in full.
2. Whether data is for individual contracts (e.g. WINJ25/WINM25/WINQ25/WINV25/WINZ25...) or a continuous WINFUT series; if continuous, provide the exact roll/mapping methodology and constituent-contract identity by timestamp/session.
3. Timezone used in timestamps and daylight/session handling.
4. Trading-session boundaries and treatment of auctions, after-market, corrections and canceled/corrected trades.
5. Publication timing: when historical records become available relative to each trading session.
6. Revision policy: whether previously delivered records can change later; if yes, how revisions/corrections are identified/versioned.
7. Point-in-time reproducibility: whether historical files as originally published can be retrieved/versioned, or whether only the latest revised history is available.
8. File/API format and required fields: timestamp, symbol/contract, open/high/low/close, volume or trade quantity; for tick data, trade ID/sequence if available.
9. Whether files can be delivered with hashes/checksums, immutable filenames/versions, or another way to bind a dataset cryptographically.
10. A small sample for one 2025 WIN contract/session plus schema/data dictionary before purchase.
11. Price and licensing terms for research/backtesting use.
12. If your product cannot satisfy all points, please identify which requirements it does and does not satisfy.

Important: we cannot accept reconstructed/backfilled scientific credit, silent symbol substitution, or undocumented continuous-series stitching. We need provenance sufficient for an auditable historical study.
