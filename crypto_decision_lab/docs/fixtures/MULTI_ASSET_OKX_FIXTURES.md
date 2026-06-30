# Multi-Asset OKX Public Fixtures

Sprint 7D expands the offline OKX-shaped fixture set.

Current fixture coverage:

```text
BTC-USDT
ETH-USDT
SOL-USDT
```

The fixtures remain local, static and research-only.

They are not downloaded live and they do not require:

```text
API key
account connection
authenticated exchange access
orders
real capital
```

## Replay usage

From the repository root:

```bash
bash qrds_full_research.sh \
  --fixture data/fixtures/okx_public/okx_public_eth_usdt_1h_sample.json \
  --output-dir artifacts/full_research_eth \
  --run-id full-research-eth \
  --report-id edge-report-eth
```

Use the same pattern for BTC or SOL fixtures.
