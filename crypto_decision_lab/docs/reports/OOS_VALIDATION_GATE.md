# QRDS/QOS — Out-of-Sample Validation Gate v1

Sprint 8Q adds a research-only out-of-sample validation gate packet.

## Question answered

> Does the research evidence stack have enough held-out validation support to continue toward the next research gate?

## What this gate may do

- Read prior research artifacts from 8L, 8M, 8N, 8O, and 8P.
- Evaluate whether the evidence stack includes enough prior reports, walk-forward splits, sample coverage, leakage/embargo checks, metric stability, and formal OOS artifact presence.
- Build a static HTML/JSON/Markdown packet for review.
- Keep all operational paths locked.

## What this gate may not do

- It may not generate recommendations.
- It may not create orders.
- It may not create executable signals.
- It may not allocate capital or produce portfolio decisions.
- It may not use API keys, accounts, authenticated exchange access, or real capital.
- It may not change `INTERACTIVE_RESEARCH_ONLY`.

## Expected usage

```bash
cd /workspaces/QRDS

bash qrds_oos_validation_serve.sh \
  --output-dir artifacts/oos_validation \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Using existing 8L/8M/8N/8O/8P artifacts:

```bash
bash qrds_oos_validation_serve.sh \
  --output-dir artifacts/oos_validation \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json,crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json,crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json,crypto_decision_lab/artifacts/human_review/human_review_gate.json
```

Then open the Codespaces port printed by the wrapper:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Interpretation

This sprint creates an OOS validation packet and readiness matrix. It does not prove a live edge and does not unlock any operational use.
