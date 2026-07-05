#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase32_risk_regime_dashboard_navigation_hardening_pack_serve.sh" "$@"
