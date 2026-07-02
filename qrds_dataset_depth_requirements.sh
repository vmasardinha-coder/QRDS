#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
PYTHONPATH="$PWD/src:${PYTHONPATH:-}" python -m crypto_decision_lab.cli.dataset_depth_requirements "$@"
