#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="artifacts/research_book_legacy_intake"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
BOOK_DIR="docs/book"
IMPORTS_DIR=""
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --symbols) SYMBOLS="$2"; shift 2 ;;
    --book-dir) BOOK_DIR="$2"; shift 2 ;;
    --imports-dir) IMPORTS_DIR="$2"; shift 2 ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done
cd "$ROOT_DIR/crypto_decision_lab"
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
CMD=(python -m crypto_decision_lab.cli.research_book_legacy_intake --output-dir "$OUTPUT_DIR" --symbols "$SYMBOLS" --book-dir "$BOOK_DIR")
if [[ -n "$IMPORTS_DIR" ]]; then
  CMD+=(--imports-dir "$IMPORTS_DIR")
fi
"${CMD[@]}" "${EXTRA_ARGS[@]}"
