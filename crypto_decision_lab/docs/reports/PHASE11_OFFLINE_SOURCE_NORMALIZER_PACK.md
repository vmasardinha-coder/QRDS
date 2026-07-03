# QRDS/QOS Phase 11 Offline Source Normalizer Pack

Sprint 11I–11P prepares offline `.csv` / `.jsonl` source normalization.

It scans the manual inbox, maps common OHLCV aliases into canonical fields, writes normalized JSONL under artifacts, and keeps canonical promotion blocked.

Primary launcher:

```bash
bash qrds_phase11_offline_source_normalizer_pack_serve.sh
```
