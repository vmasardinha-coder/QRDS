#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase15_multisource_trust_registry_comparison_pack}"
python -m crypto_decision_lab.cli.phase15_multisource_trust_registry_comparison_pack --output-dir "$OUT" --repo-root "$ROOT"
