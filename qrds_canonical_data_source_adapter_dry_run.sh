#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/canonical_data_source_adapter_dry_run}"
python -m crypto_decision_lab.cli.canonical_data_source_adapter_dry_run \
  --output-dir "$OUT" \
  --repo-root "$ROOT"
