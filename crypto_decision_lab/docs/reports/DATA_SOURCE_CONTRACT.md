# QRDS/QOS Data Source Contract / Canonical Schema Pack

Sprint 9O defines the canonical source and schema contract for research-only datasets before deeper data expansion.

The contract is intentionally blocking. It does not approve operational use. It defines what a dataset must look like so future depth expansion does not create large but unusable files.

## Canonical bar dataset v1

Required metadata:

- `symbol`
- `interval`
- `source`

Required bar/candle fields:

- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`

Allowed dataset prefixes:

- `crypto_decision_lab/data/fixtures/`
- `crypto_decision_lab/data/research/`
- `crypto_decision_lab/data/canonical/`
- `crypto_decision_lab/data/raw/`
- `crypto_decision_lab/data/validated/`

Rejected source locations include artifacts, docs, tests, caches, and generated portals.

## Safety posture

This pack is research-only. It cannot create orders, signals, allocations, live exchange workflows, or capital actions.
