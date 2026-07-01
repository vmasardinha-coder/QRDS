# QRDS Evidence Drilldown / Data Coverage Gate v1

Sprint 8M adds a research-only drilldown layer after Sprint 8L.

It answers:

> Why did the evidence pass, fail, or remain under watch for research?

It expands each asset into research-only dimensions:

- data volume;
- walk-forward split coverage;
- stress stability;
- edge quality;
- artifact lineage.

It does **not** produce operational decisions, executable signals, recommendations, allocation, portfolio weights, position sizing, orders, real-capital actions, authenticated exchange access, or API-key usage.

## Generate artifacts from deterministic fixtures

From the repository root:

```bash
cd /workspaces/QRDS

bash qrds_evidence_drilldown.sh \
  --output-dir artifacts/evidence_drilldown \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Because the root wrapper delegates into `crypto_decision_lab`, the relative output directory above is created under:

```text
/workspaces/QRDS/crypto_decision_lab/artifacts/evidence_drilldown
```

## Generate artifacts from an existing 8L Evidence Quality report

```bash
cd /workspaces/QRDS

bash qrds_evidence_drilldown.sh \
  --output-dir artifacts/evidence_drilldown \
  --evidence-report crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json
```

## Serve in Codespaces

Use the serve wrapper for reliable HTML opening through a local server/port:

```bash
cd /workspaces/QRDS

bash qrds_evidence_drilldown_serve.sh \
  --output-dir artifacts/evidence_drilldown \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

The terminal remains attached to the HTTP server. Stop it with `Ctrl+C`.

## Interpretation

- `PASS`: this dimension can continue through research review.
- `WATCH`: evidence is partial and needs reinforcement.
- `FAIL`: the dimension blocks later gates until more evidence is collected.

Even when the drilldown says `PASS`, the project remains in `INTERACTIVE_RESEARCH_ONLY` mode. The next gates remain mandatory:

1. data coverage gate;
2. data quality/reliability gate;
3. out-of-sample validation;
4. paper trading;
5. risk model;
6. human approval;
7. explicit policy change from research-only.

## Artifacts

The CLI writes:

- `evidence_drilldown_gate.json`
- `evidence_drilldown_gate.md`
- `evidence_drilldown_index.json`
- `index.html`
