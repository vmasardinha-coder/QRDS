#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase18_research_feature_regime_diagnostics_pack}"
python -m crypto_decision_lab.cli.phase18_research_feature_regime_diagnostics_pack --output-dir "$OUT" --repo-root "$ROOT"
