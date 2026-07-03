#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="${1:-$PROJECT/artifacts/installer_archive_plan}"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
cd "$PROJECT"
python -m crypto_decision_lab.cli.installer_archive_plan --output-dir "$OUT" --repo-root "$ROOT"
