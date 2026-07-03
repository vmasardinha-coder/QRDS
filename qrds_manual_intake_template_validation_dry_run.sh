#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/manual_intake_template_validation_dry_run}"
python -m crypto_decision_lab.cli.manual_intake_template_validation_dry_run \
  --output-dir "$OUT" \
  --repo-root "$ROOT"
