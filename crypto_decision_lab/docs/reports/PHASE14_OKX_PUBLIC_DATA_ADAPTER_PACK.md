# QRDS/QOS Phase 14 OKX Public Data Adapter Pack

Sprint 14I–14R adds an OKX public-market adapter.

Scope:

- OKX public market candles endpoint family;
- BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP;
- 1H bar;
- 5000 rows per instrument;
- separate `manual_intake/okx_inbox`;
- no API key;
- no account connection;
- no order endpoint;
- no signals/recommendations;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase14_okx_public_data_adapter_pack_serve.sh
```
