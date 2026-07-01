#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
python -m crypto_decision_lab.cli.research_book_reader "$@"
