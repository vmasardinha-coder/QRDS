#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/archive_manifest_repo_hygiene}"
python -m crypto_decision_lab.cli.archive_manifest_repo_hygiene --output-dir "$OUT" --repo-root "$ROOT"
