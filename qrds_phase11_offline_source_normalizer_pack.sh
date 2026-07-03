#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase11_offline_source_normalizer_pack}"
python -m crypto_decision_lab.cli.phase11_offline_source_normalizer_pack --output-dir "$OUT" --repo-root "$ROOT"
