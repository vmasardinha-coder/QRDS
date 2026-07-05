#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase31_risk_regime_research_dashboard_mvp_pack_serve.sh" "$@"
