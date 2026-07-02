#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
export PYTHONPATH="$ROOT/crypto_decision_lab/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.data_readiness "$@"
