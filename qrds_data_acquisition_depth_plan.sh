#!/usr/bin/env bash
set -euo pipefail
cd "${REPO_ROOT:-/workspaces/QRDS}/crypto_decision_lab"
python -m crypto_decision_lab.cli.data_acquisition_depth_plan "$@"
