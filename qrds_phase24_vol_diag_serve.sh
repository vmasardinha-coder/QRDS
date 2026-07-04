#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase24_volatility_residual_diagnostics_baseline_robustness_pack_serve.sh" "$@"
