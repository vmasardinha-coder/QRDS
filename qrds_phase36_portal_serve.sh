#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase36_unified_risk_regime_research_portal_shell_pack_serve.sh" "$@"
