#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/crypto_decision_lab"
python -m crypto_decision_lab.cli.data_source_contract "$@"
