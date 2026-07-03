# QRDS/QOS Phase 12 Public Data Research Readiness Certification Pack

Sprint 12S–12Z certifies whether public OHLCV data is research-ready across the full data-drop pipeline.

It verifies:

- public Binance kline files exist in inbox;
- synthetic fixtures are not present in inbox;
- 5000 rows per symbol for BTC-USDT, ETH-USDT, SOL-USDT;
- source labels are public-data research-only;
- acceptance pipeline is in INBOX_DATA mode;
- normalized/valid/staged rows meet target depth;
- sample quality and full depth are ready;
- canonical writes remain zero;
- safe apply and promotion remain blocked;
- operational decisions remain blocked.

Primary launcher:

```bash
bash qrds_phase12_public_data_research_readiness_certification_pack_serve.sh
```
