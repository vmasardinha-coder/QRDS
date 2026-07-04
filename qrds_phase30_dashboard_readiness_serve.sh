#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_serve.sh" "$@"
