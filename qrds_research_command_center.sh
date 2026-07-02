#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT/crypto_decision_lab"
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.research_command_center "$@"
