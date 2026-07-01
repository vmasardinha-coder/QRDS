# Research Book Chronicle v1

Sprint 8X adds a lightweight maintenance layer for the QRDS/QOS long-form research book.

## Purpose

The chronicle records:

- planned chapter coverage;
- discovered chapter files;
- supporting documentation sources;
- book update cadence;
- policy-lock state;
- research-only guardrails.

## Non-operational boundary

This is a documentation governance artifact. It does not approve execution, account connection, authenticated exchange access, orders, recommendations, allocation, position sizing, or real-capital deployment.

## Usage

```bash
cd /workspaces/QRDS
bash qrds_research_book_chronicle_serve.sh \
  --output-dir artifacts/research_book_chronicle \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Open with:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```
