#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT/crypto_decision_lab"
export PYTHONPATH="src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.data_audit "$@"
