# QRDS Offline Source Normalizer

Drop `.csv` or `.jsonl` files here. Preferred fields:

```text
timestamp, open, high, low, close, volume, symbol, interval, source
```

Supported aliases include `open_time`, `time`, `datetime`, `o`, `h`, `l`, `c`, `v`, `base_volume`, `pair`, `market`, and `timeframe`.

Normalized outputs are artifact-only. Nothing is promoted into canonical data directories by this normalizer.
