#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/post_cleanup_portal_acceptance}"
python -m crypto_decision_lab.cli.post_cleanup_portal_acceptance \
  --output-dir "$OUT" \
  --repo-root "$ROOT"
