# QRDS Evidence Quality Gate v1

Sprint 8L adds a research-only Evidence Quality Gate for the QRDS/QOS project inside Gate BTC.

The gate answers one research question:

> Is this hypothesis becoming reliable enough for continued research?

It evaluates:

- data volume;
- walk-forward split count;
- stress stability;
- edge status;
- research readiness.

It does **not** produce operational decisions, executable signals, recommendations, allocation, portfolio weights, position sizing, orders, real-capital actions, authenticated exchange access or API-key usage.

## Generate artifacts

From the repository root:

```bash
cd /workspaces/QRDS

bash qrds_evidence_quality.sh \
  --output-dir artifacts/evidence_quality \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Because the root wrapper delegates into `crypto_decision_lab`, the relative output directory above is created under:

```text
/workspaces/QRDS/crypto_decision_lab/artifacts/evidence_quality
```

## Serve in Codespaces

Use the serve wrapper for reliable HTML opening through a local server/port:

```bash
cd /workspaces/QRDS

bash qrds_evidence_quality_serve.sh \
  --output-dir artifacts/evidence_quality \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

The terminal remains attached to the HTTP server. Stop it with `Ctrl+C`.

## Optional upstream artifacts

The CLI can consume existing upstream report/index JSON files:

```bash
bash qrds_evidence_quality.sh \
  --output-dir artifacts/evidence_quality \
  --multi-asset-index artifacts/multi_asset/multi_asset_research_index.json \
  --stress-index artifacts/scenario_stress/scenario_stress_index.json
```

If upstream indexes are not supplied, the CLI writes deterministic offline fixtures under `upstream_research_inputs/`. These fixtures are only for local research UX/testing and remain `INTERACTIVE_RESEARCH_ONLY`.

## Output files

The sprint writes:

- `evidence_quality_gate.json`
- `evidence_quality_gate.md`
- `index.html`
- `evidence_quality_index.json`
- optional fixture upstream inputs when no upstream indexes are supplied

## Safety contract

All generated artifacts keep the safety flags false:

```text
operational_decision_allowed = False
orders_generated = False
real_capital_used = False
trading_signal_generated = False
executable_signal_generated = False
recommendation_generated = False
allocation_generated = False
portfolio_decision_generated = False
```

The mode remains:

```text
app_mode = INTERACTIVE_RESEARCH_ONLY
```

## Full validation

From the Python project root:

```bash
cd /workspaces/QRDS/crypto_decision_lab
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs
```
