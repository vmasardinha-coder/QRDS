#!/usr/bin/env bash
set -euo pipefail
cd "${QRDS_REPO_ROOT:-/workspaces/QRDS}/crypto_decision_lab"
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.cli.portal_reconciliation \
  --output-dir "${1:-artifacts/portal_reconciliation}" \
  --repo-root "${QRDS_REPO_ROOT:-/workspaces/QRDS}"
