# QRDS Static Research Dashboard v1

Sprint 8C adds the first user-facing visual layer.

It generates an offline static HTML dashboard from the research artifacts.

## Command from repository root

```bash
bash qrds_dashboard.sh \
  --output-dir artifacts/dashboard \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Open:

```text
artifacts/dashboard/dashboard/index.html
```

## What it shows

```text
asset cards
edge status
edge score
worst stress status
worst stress score
descriptive ranking
scenario summaries
safety locks
```

## Safety

This is a dashboard, not an execution app.

It does not produce:

```text
allocation
portfolio weights
position sizing
signals
orders
recommendations
operational decisions
real-capital actions
```

## User application level

This is the first practical user-visible layer.

The next usability steps can be:

```text
filters
more charts
artifact browser
local web server wrapper
public no-auth data refresh
```
