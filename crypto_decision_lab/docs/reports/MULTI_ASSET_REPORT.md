# QRDS Multi-Asset Report Aggregator

Sprint 8A aggregates multiple symbol-level research report packs into one
research-only multi-asset overview.

## Command from repository root

```bash
bash qrds_multi_asset_report.sh \
  --output-dir artifacts/multi_asset_report
```

Optional symbol filter:

```bash
bash qrds_multi_asset_report.sh \
  --output-dir artifacts/multi_asset_report \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

## Outputs

```text
full_research/<symbol>/
report_packs/<symbol>/
multi_asset_report/multi_asset_research_report.json
multi_asset_report/multi_asset_research_report.md
multi_asset_report/multi_asset_entries.json
multi_asset_report/multi_asset_research_index.json
```

## Safety

This is not an allocation engine.

It does not produce:

```text
portfolio weights
position sizing
orders
signals
recommendations
operational decisions
real-capital actions
```
