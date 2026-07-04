#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase23_volatility_first_research_benchmark_pack_serve.sh" "$@"
