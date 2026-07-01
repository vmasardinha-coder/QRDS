# QRDS/QOS Research Book Refresh

Sprint 8W resumes the long-form QRDS/QOS book that started earlier in the project.
The book is now synchronized with the current Gate BTC research stack and remains
strictly `INTERACTIVE_RESEARCH_ONLY`.

## What this sprint adds

- `docs/book/BOOK_MANIFEST.md`
- `docs/book/CHAPTER_INDEX.md`
- `docs/book/chapters/CHAPTER_00_...` through `CHAPTER_19_...`
- `src/crypto_decision_lab/reports/research_book.py`
- `src/crypto_decision_lab/cli/research_book.py`
- `qrds_research_book.sh`
- `qrds_research_book_serve.sh`
- tests for the book generator and CLI

## Purpose

The book answers:

> Where are we in the QRDS/QOS architecture, what has been built, what remains
> blocked, and what chapters still need research evidence?

It does **not** answer:

- buy
- sell
- allocate
- position sizing
- order execution
- real-capital use
- operational recommendation

## Usage

```bash
cd /workspaces/QRDS
bash qrds_research_book_serve.sh \
  --output-dir artifacts/research_book \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```
