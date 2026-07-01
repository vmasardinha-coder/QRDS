# QRDS Evidence Timeline / Gate History Registry v1

Sprint 8N adds a research-only history layer after Sprint 8L and Sprint 8M.

It answers:

> Is the research evidence repeatable across registered gates/runs, or is it just one artifact?

It evaluates:

- number of registered evidence observations;
- which gates were seen for each symbol;
- latest research-readiness score;
- status consistency across reports;
- score regression from prior registered evidence;
- source artifact hashes and auditability.

It does **not** answer:

- whether to buy;
- whether to sell;
- how much to allocate;
- position sizing;
- portfolio action;
- order placement;
- real-capital usage.

Required safety flags remain false:

- `operational_decision_allowed = False`
- `orders_generated = False`
- `real_capital_used = False`
- `trading_signal_generated = False`
- `executable_signal_generated = False`
- `recommendation_generated = False`
- `allocation_generated = False`
- `portfolio_decision_generated = False`

## Usage

From the repository root in Codespaces:

```bash
cd /workspaces/QRDS
bash qrds_evidence_timeline.sh \
  --output-dir artifacts/evidence_timeline \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

To serve the dashboard:

```bash
cd /workspaces/QRDS
bash qrds_evidence_timeline_serve.sh \
  --output-dir artifacts/evidence_timeline \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

To use real local 8L/8M research artifacts:

```bash
bash qrds_evidence_timeline_serve.sh \
  --output-dir artifacts/evidence_timeline \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json
```

## Interpretation

- `PASS`: the evidence history is stable enough to continue research-only investigation.
- `WATCH`: the history is partial or inconsistent; collect more runs.
- `FAIL`: the history is insufficient, missing required gates, regressed, or latest evidence is weak.

A `PASS` is not permission to operate. Later gates remain mandatory:

1. repeated evidence timeline across multiple research runs;
2. data quality / reliability gate;
3. out-of-sample validation;
4. paper trading;
5. formal risk model;
6. human approval;
7. explicit policy change away from research-only.
