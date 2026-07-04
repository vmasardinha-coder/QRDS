#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase26_regime_segmented_volatility_edge_audit_pack_serve.sh" "$@"
