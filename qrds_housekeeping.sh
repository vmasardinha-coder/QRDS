#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
cd crypto_decision_lab
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m crypto_decision_lab.cli.housekeeping --repo-root .. "$@"
