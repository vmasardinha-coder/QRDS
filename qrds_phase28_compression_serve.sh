#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase28_regime_taxonomy_compression_failure_analysis_pack_serve.sh" "$@"
