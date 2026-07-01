# QRDS/QOS • Research Book Reader Portal v1

Sprint 8Z creates a friendlier static reader for the QRDS/QOS research book.

It indexes the planned 20-chapter book, discovers existing chapter Markdown files,
links legacy imports, and exports a local portal with HTML, Markdown, JSON, and PDF
artifacts.

## Scope

This is a documentation and governance artifact only. It does not generate signals,
recommendations, allocations, orders, position sizing, or any real-capital workflow.

## Commands

```bash
cd /workspaces/QRDS
bash qrds_research_book_reader.sh --output-dir artifacts/research_book_reader --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

```bash
cd /workspaces/QRDS
bash qrds_research_book_reader_serve.sh --output-dir artifacts/research_book_reader --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Expected answer

```text
RESEARCH_BOOK_READER_PORTAL_READY_POLICY_LOCK_ACTIVE_RESEARCH_ONLY
```

The policy lock must remain active and all operational safety flags must remain false.
