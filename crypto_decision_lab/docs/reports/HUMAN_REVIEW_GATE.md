# QRDS/QOS — Human Review / Policy Lock Gate v1

Sprint 8P adds a research-only human review and policy lock packet.

## Question answered

> Has the evidence stack been formally reviewed by a human, and does the policy still block operational promotion?

## What this gate may do

- Read prior research reports from 8L, 8M, 8N, and 8O.
- Build a review packet with current research gates, future formal gates, and human-review state.
- Record whether a research reviewer has marked the material as not reviewed, under review, research-approved with blockers, or rejected.
- Keep the policy lock active.

## What this gate may not do

- It may not create or imply trade recommendations.
- It may not generate orders.
- It may not generate executable signals.
- It may not allocate capital or build a portfolio decision.
- It may not approve real capital use.
- It may not change `INTERACTIVE_RESEARCH_ONLY`.

## Expected usage

```bash
cd /workspaces/QRDS

bash qrds_human_review_serve.sh \
  --output-dir artifacts/human_review \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Using existing 8L/8M/8N/8O artifacts:

```bash
bash qrds_human_review_serve.sh \
  --output-dir artifacts/human_review \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json,crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json,crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json \
  --review-state UNDER_REVIEW \
  --reviewer Victor
```

Then open the Codespaces port printed by the wrapper:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Interpretation

The result remains research-only even when review notes exist. This sprint is a policy lock artifact, not a policy change artifact.
