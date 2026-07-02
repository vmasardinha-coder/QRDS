#!/usr/bin/env bash
set -euo pipefail
cd "${QRDS_REPO_ROOT:-/workspaces/QRDS}"
bash qrds_portal_reconciliation_serve.sh "${1:-artifacts/portal_reconciliation}"
