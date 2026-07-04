# QRDS/QOS Phase 13 Hyperliquid Public Data Adapter Pack

Sprint 13I–13R adds a public-data Hyperliquid adapter.

Scope:

- public `POST https://api.hyperliquid.xyz/info`;
- `candleSnapshot` only;
- BTC, ETH, SOL by default;
- 1h interval;
- 5000 rows per coin;
- separate `manual_intake/hyperliquid_inbox`;
- no API wallet;
- no account connection;
- no `/exchange` endpoint;
- no orders;
- no signals/recommendations;
- zero canonical writes.

Primary launcher:

```bash
bash qrds_phase13_hyperliquid_public_data_adapter_pack_serve.sh
```
