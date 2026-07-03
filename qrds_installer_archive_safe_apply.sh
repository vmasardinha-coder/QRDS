#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
OUT="$PROJECT/artifacts/installer_archive_safe_apply"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
mkdir -p "$OUT"
cd "$PROJECT"
python -m crypto_decision_lab.cli.installer_archive_safe_apply --output-dir "$OUT" --repo-root "$ROOT"
