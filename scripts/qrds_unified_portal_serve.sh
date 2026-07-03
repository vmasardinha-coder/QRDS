#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
cd "$ROOT"
bash qrds_unified_portal_serve.sh
