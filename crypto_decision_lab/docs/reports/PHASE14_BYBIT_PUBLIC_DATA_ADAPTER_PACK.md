# QRDS/QOS Phase 14 Bybit Public Data Adapter Pack

Sprint 14A–14H adds a Bybit public-market adapter.

Scope:

- Bybit V5 public `GET /v5/market/kline`;
- category `linear` by default;
- BTCUSDT, ETHUSDT, SOLUSDT;
- 1h interval (`60`);
- 5000 rows per symbol;
- separate `manual_intake/bybit_inbox`;
- no API key;
- no account connection;
- no order endpoint;
- no signals/recommendations;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase14_bybit_public_data_adapter_pack_serve.sh
```
