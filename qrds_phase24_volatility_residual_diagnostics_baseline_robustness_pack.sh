#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase24_volatility_residual_diagnostics_baseline_robustness_pack}"
python -m crypto_decision_lab.cli.phase24_volatility_residual_diagnostics_baseline_robustness_pack --output-dir "$OUT" --repo-root "$ROOT"
