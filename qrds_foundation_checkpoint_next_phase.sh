#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/foundation_checkpoint_next_phase}"
python -m crypto_decision_lab.cli.foundation_checkpoint_next_phase \
  --output-dir "$OUT" \
  --repo-root "$ROOT"
