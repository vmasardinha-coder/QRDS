# QRDS Evidence Stack Runner v1

Sprint 8S adds a single-command runner/launcher for the research-only evidence gate stack.

It solves the manual sequencing problem:

```text
8L Evidence Quality
↓
8M Evidence Drilldown
↓
8N Evidence Timeline
↓
8O Research Promotion Matrix
↓
8P Human Review / Policy Lock
↓
8Q Out-of-Sample Validation
↓
8R Paper Trading Gate, when installed
↓
Evidence Stack Hub
```

The runner passes the generated JSON reports forward automatically, so the user does not need to remember report paths.

## Generate the full stack

From the repository root:

```bash
cd /workspaces/QRDS

bash qrds_evidence_stack.sh \
  --output-dir artifacts/evidence_stack \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

## Serve the full stack in Codespaces

Use the serve wrapper for reliable opening via server/port:

```bash
cd /workspaces/QRDS

bash qrds_evidence_stack_serve.sh \
  --output-dir artifacts/evidence_stack \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

The terminal remains attached to the HTTP server. Stop it with `Ctrl+C`.

## Research-only policy

This runner cannot unlock operational usage. It does not produce:

- buy/sell decisions;
- trade recommendations;
- executable signals;
- allocation or portfolio decisions;
- position sizing;
- orders;
- API-key usage;
- authenticated exchange connections;
- real-capital activity.

The policy lock remains active until an explicit external policy change is made outside this research-only software path.

## Path convention

All gate wrappers execute inside `crypto_decision_lab`, so the stack runner passes report paths relative to that project root, for example:

```text
artifacts/evidence_stack/evidence_quality/evidence_quality_gate.json
```

This avoids the earlier ambiguity between:

```text
/workspaces/QRDS/crypto_decision_lab/artifacts/...
```

and:

```text
crypto_decision_lab/artifacts/...
```
