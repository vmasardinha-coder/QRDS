# QRDS Source Requests

Manual/offline research data expansion requests.

Accepted inbox formats:

```text
.jsonl
.csv
```

Required canonical fields:

```text
timestamp, open, high, low, close, volume, symbol, interval, source
```

Drop manually prepared files into:

```text
crypto_decision_lab/manual_intake/inbox/
```

No API keys, authenticated exchange accounts, live trading accounts, automatic collectors, orders, or capital workflows are used here.
