# Edge Report Artifact Export

## Purpose

Sprint 7B exports Edge Report v1 artifacts to disk.

The export is still research-only.

## Files

For each report id:

```text
edge_report.json
edge_summary.json
edge_export_index.json
```

## Safety

The exporter blocks unsafe artifacts if any of these flags are `True`:

```text
operational_decision_allowed
api_key_required
api_key_present
account_connection_required
orders_generated
real_capital_used
orders_allowed
trading_signal_generated
executable_signal_generated
recommendation_generated
```

## Not allowed

The exported Edge Report is not:

- a recommendation
- a trading signal
- an order
- a live strategy
- a real-money decision
