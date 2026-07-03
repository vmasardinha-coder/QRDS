#!/usr/bin/env bash
set -euo pipefail
cd "${QRDS_ROOT:-/workspaces/QRDS}"
bash qrds_unified_portal_serve.sh
