#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-/workspaces/QRDS}"
cd "$ROOT/crypto_decision_lab"
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.workspace_cleanup_plan --output-dir artifacts/workspace_cleanup_plan
