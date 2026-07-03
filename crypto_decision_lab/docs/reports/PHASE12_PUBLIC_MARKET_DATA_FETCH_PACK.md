# QRDS/QOS Phase 12 Public Market Data Fetch Pack

Sprint 12I–12R fetches public Binance Spot kline/candlestick OHLCV data into the manual inbox.

Default scope:

- BTCUSDT, ETHUSDT, SOLUSDT;
- 1h interval;
- 5000 rows per symbol;
- public market-data endpoints only;
- no API key;
- no account connection;
- no trading endpoint;
- zero canonical writes;
- promotion remains blocked.

Primary launcher:

```bash
bash qrds_phase12_public_market_data_fetch_pack_serve.sh
```

Full public data pipeline:

```bash
bash qrds_phase12_run_public_market_data_pipeline.sh
```
