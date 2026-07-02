#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
OUT="${1:-artifacts/workspace_cleanup_dry_run}"
APPLY_FLAG=""
if [ "${QRDS_APPLY_LOW_RISK_CLEANUP:-0}" = "1" ]; then
  APPLY_FLAG="--apply-low-risk"
fi
python -m crypto_decision_lab.cli.workspace_cleanup_dry_run \
  --output-dir "$OUT" \
  --repo-root "$ROOT" \
  $APPLY_FLAG
