#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/crypto_decision_lab"

cd "$PROJECT"

export PYTHONPATH="$PROJECT/src${PYTHONPATH:+:$PYTHONPATH}"

python -m crypto_decision_lab.cli.dashboard_hub "$@"
