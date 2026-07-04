#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase19_offline_experiment_harness_pack}"
python -m crypto_decision_lab.cli.phase19_offline_experiment_harness_pack --output-dir "$OUT" --repo-root "$ROOT"
