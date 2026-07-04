#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase20_baseline_metrics_null_models_harness_pack}"
python -m crypto_decision_lab.cli.phase20_baseline_metrics_null_models_harness_pack --output-dir "$OUT" --repo-root "$ROOT"
